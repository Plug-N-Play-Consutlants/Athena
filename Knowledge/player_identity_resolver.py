"""
Canonical player identity resolver.

Purpose:
- Bridge fantasy-provider player identities to public sport-provider identities.
- First pass: Fantrax player_master -> NHL skater summary.

Inputs:
    Output/player_master.json
    Raw/nhl_skater_summary.json

Outputs:
    Output/player_identity_map.json
    Output/player_identity_map.csv

Layer responsibility:
- Knowledge layer only.
- No valuation, recommendations, or business logic.
- Does not mutate provider raw data.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from collections import defaultdict
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

import sys

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.json_utils import read_json, write_json
from Core.logger import log, log_header, log_section
from Core.project_paths import OUTPUT_DIR, RAW_DIR

PLAYER_MASTER_PATH = OUTPUT_DIR / "player_master.json"
NHL_SKATER_SUMMARY_PATH = RAW_DIR / "nhl_skater_summary.json"
NHL_IDENTITY_CANDIDATES_PATH = RAW_DIR / "nhl_identity_candidates.json"
FANTRAX_TRANSACTION_SOURCE_PATH = RAW_DIR / "transactions.json"
FANTRAX_PERIOD_ROSTERS_DIR = OUTPUT_DIR / "PeriodRosters"

OUTPUT_JSON = OUTPUT_DIR / "player_identity_map.json"
OUTPUT_CSV = OUTPUT_DIR / "player_identity_map.csv"


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        # NHL API sometimes returns localized fields such as {"default": "..."}.
        for key in ("default", "en", "value", "name"):
            if key in value:
                return _safe_str(value.get(key))
        return ""
    return str(value).strip()


def _normalize_text(value: Any) -> str:
    text = _safe_str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower()
    text = text.replace(".", " ").replace("-", " ").replace("'", "")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _fantrax_display_name(raw_name: Any) -> str:
    """Convert Fantrax-style 'Last, First' names to 'First Last' when needed."""
    name = _safe_str(raw_name)
    if "," in name:
        last, first = [part.strip() for part in name.split(",", 1)]
        if first and last:
            return f"{first} {last}"
    return name


def _extract_nhl_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]

    if not isinstance(payload, dict):
        return []

    for key in ("data", "players", "skaters", "results", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]

    # Some wrappers return nested payloads.
    for key in ("payload", "response", "stats"):
        value = payload.get(key)
        if isinstance(value, dict):
            rows = _extract_nhl_rows(value)
            if rows:
                return rows

    return []


def _extract_nhl_player_id(row: dict[str, Any]) -> str:
    for key in ("playerId", "player_id", "id", "personId", "skaterId"):
        value = row.get(key)
        if value not in (None, ""):
            return _safe_str(value)
    return ""


def _extract_nhl_player_name(row: dict[str, Any]) -> str:
    for key in (
        "skaterFullName",
        "playerFullName",
        "fullName",
        "name",
        "playerName",
        "player_name",
    ):
        value = row.get(key)
        if value:
            return _safe_str(value)

    first = _safe_str(row.get("firstName") or row.get("first_name"))
    last = _safe_str(row.get("lastName") or row.get("last_name"))
    if first or last:
        return f"{first} {last}".strip()

    return ""


def _extract_nhl_team(row: dict[str, Any]) -> str:
    for key in (
        "teamAbbrevs",
        "teamAbbrev",
        "team_abbrev",
        "currentTeamAbbrev",
        "team",
        "currentTeam",
    ):
        value = row.get(key)
        if isinstance(value, dict):
            value = value.get("default") or value.get("abbrev") or value.get("triCode")
        text = _safe_str(value)
        if text:
            # NHL summary can return comma-delimited team abbreviations if a player changed teams.
            return text.split(",")[-1].strip().upper()
    return ""


def _extract_nhl_position(row: dict[str, Any]) -> str:
    for key in ("positionCode", "position", "positionAbbrev", "pos"):
        value = row.get(key)
        if isinstance(value, dict):
            value = value.get("code") or value.get("abbrev") or value.get("default")
        text = _safe_str(value).upper()
        if text:
            return text
    return ""


def _build_nhl_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One permanent NHL ID per player; names across seasons are searchable aliases.

    Historical name changes (including transliterations) can be meaningful,
    but cannot justify merging two *different* NHL IDs with the same name.
    """
    by_nhl_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        name = _extract_nhl_player_name(row)
        player_id = _extract_nhl_player_id(row)
        if not name or not player_id:
            continue
        previous = by_nhl_id.get(player_id) or {}
        aliases = set(previous.get("normalized_aliases") or ())
        aliases.add(_normalize_text(name))
        by_nhl_id[player_id] = {
            "nhl_player_id": player_id,
            "nhl_player_name": name,
            "nhl_team": _extract_nhl_team(row) or previous.get("nhl_team", ""),
            "nhl_position": _extract_nhl_position(row) or previous.get("nhl_position", ""),
            "normalized_name": _normalize_text(name),
            "normalized_aliases": sorted(aliases),
            "raw": row,
        }
    return list(by_nhl_id.values())


def _positions_compatible(fantrax_position: str, nhl_position: str) -> bool:
    """Compare documented position families without conflating different roles."""
    normalize = {"LW": "L", "RW": "R", "LD": "D", "RD": "D"}
    fantasy = {normalize.get(p.strip().upper(), p.strip().upper())
               for p in re.split(r"[,/|\s]+", fantrax_position or "") if p.strip()}
    pro = normalize.get(_safe_str(nhl_position).upper(), _safe_str(nhl_position).upper())
    return bool(pro and pro in fantasy)


def _match_player(
    fantrax_player: dict[str, Any],
    nhl_candidates: list[dict[str, Any]],
    name_index: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    fantrax_id = _safe_str(fantrax_player.get("player_id") or fantrax_player.get("fantrax_player_id"))
    fantrax_raw_name = _safe_str(fantrax_player.get("player_name") or fantrax_player.get("name"))
    fantrax_display_name = _fantrax_display_name(fantrax_raw_name)
    fantrax_name_key = _normalize_text(fantrax_display_name)
    fantrax_team = _safe_str(fantrax_player.get("nhl_team") or fantrax_player.get("pro_team")).upper()
    fantrax_position = _safe_str(fantrax_player.get("position") or fantrax_player.get("pos")).upper()

    base = {
        "fantrax_player_id": fantrax_id,
        "fantrax_player_name": fantrax_raw_name,
        "canonical_player_name": fantrax_display_name,
        "fantrax_nhl_team": fantrax_team,
        "fantrax_position": fantrax_position,
        "nhl_player_id": "",
        "nhl_player_name": "",
        "nhl_team": "",
        "nhl_position": "",
        "match_confidence": 0.0,
        "resolution_status": "unresolved",
        "match_method": "none",
        "evidence": [],
    }

    exact_name_matches = name_index.get(fantrax_name_key, [])

    if exact_name_matches:
        if len(exact_name_matches) == 1:
            match = exact_name_matches[0]
            # A unique permanent NHL identity is independent of current club.
            mismatch = bool(fantrax_team and match.get("nhl_team") and
                            match["nhl_team"] not in re.split(r"[/,\s]+", fantrax_team))
            method = "unique_exact_name_affiliation_refresh" if mismatch else "unique_exact_name"
            return _resolved(base, match, 0.96 if not mismatch else 0.94, method)

        # Position is an identity discriminant, not simply a small confidence
        # bonus. NHL's L/R and Fantrax's LW/RW are equivalent categories.
        # NHL clubs are *not* stable identifiers and cannot distinguish two
        # same-name players on the same club.
        same_position = [row for row in exact_name_matches
                         if _positions_compatible(fantrax_position, row.get("nhl_position", ""))]
        if len(same_position) == 1:
            return _resolved(base, same_position[0], 0.97, "exact_name_unique_position")
        return _ambiguous(base, same_position or exact_name_matches,
                          "multiple_exact_name_position_matches" if same_position else "multiple_exact_name_matches")

    # Fuzzy fallback, weighted toward same NHL team. This is intentionally conservative.
    scored: list[tuple[float, dict[str, Any]]] = []
    for candidate in nhl_candidates:
        ratio = max(SequenceMatcher(None, fantrax_name_key, alias).ratio()
                    for alias in candidate.get("normalized_aliases", [candidate["normalized_name"]]))
        if fantrax_team and candidate.get("nhl_team") == fantrax_team:
            ratio += 0.06
        if fantrax_position and candidate.get("nhl_position") == fantrax_position:
            ratio += 0.02
        scored.append((min(ratio, 1.0), candidate))

    scored.sort(key=lambda item: item[0], reverse=True)
    if not scored:
        return base

    best_score, best = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0

    if best_score >= 0.94 and (best_score - second_score) >= 0.035:
        confidence = round(min(best_score - 0.05, 0.90), 3)
        return _resolved(base, best, confidence, "fuzzy_name_team_position")

    if best_score >= 0.90:
        return _ambiguous(base, [candidate for _, candidate in scored[:5]], "fuzzy_match_requires_review")

    base["evidence"] = [
        f"No exact NHL match for '{fantrax_display_name}'.",
        f"Best fuzzy score: {round(best_score, 3)} for {best.get('nhl_player_name', '')}.",
    ]
    return base


def _resolved(
    base: dict[str, Any],
    match: dict[str, Any],
    confidence: float,
    method: str,
) -> dict[str, Any]:
    result = dict(base)
    result.update(
        {
            "nhl_player_id": match.get("nhl_player_id", ""),
            "nhl_player_name": match.get("nhl_player_name", ""),
            "nhl_team": match.get("nhl_team", ""),
            "nhl_position": match.get("nhl_position", ""),
            "match_confidence": round(float(confidence), 3),
            "resolution_status": "resolved" if confidence >= 0.90 else "review",
            "match_method": method,
            "evidence": [
                f"Matched Fantrax '{base.get('canonical_player_name')}' to NHL '{match.get('nhl_player_name')}'.",
                f"Method: {method}.",
            ],
        }
    )
    if base.get("fantrax_nhl_team") and match.get("nhl_team"):
        result["evidence"].append(
            f"Team comparison: Fantrax={base.get('fantrax_nhl_team')} NHL={match.get('nhl_team')}."
        )
    return result


def _ambiguous(base: dict[str, Any], matches: list[dict[str, Any]], reason: str) -> dict[str, Any]:
    result = dict(base)
    result.update(
        {
            "resolution_status": "ambiguous",
            "candidate_nhl_ids": sorted({str(match.get("nhl_player_id")) for match in matches if match.get("nhl_player_id")}),
            "match_method": reason,
            "match_confidence": 0.5,
            "evidence": [
                f"Ambiguous match for '{base.get('canonical_player_name')}'.",
                "Candidates: "
                + "; ".join(
                    f"{match.get('nhl_player_name')} ({match.get('nhl_team')}, {match.get('nhl_player_id')})"
                    for match in matches[:5]
                ),
            ],
        }
    )
    return result


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "fantrax_player_id",
        "fantrax_player_name",
        "canonical_player_name",
        "fantrax_nhl_team",
        "fantrax_position",
        "nhl_player_id",
        "nhl_player_name",
        "nhl_team",
        "nhl_position",
        "match_confidence",
        "resolution_status",
        "match_method",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def _prior_verified_by_id(rows: Any) -> dict[str, dict[str, Any]]:
    """Treat past verified matches as durable identity links, never as club records."""
    if not isinstance(rows, list):
        return {}
    result = {}
    for row in rows:
        if not isinstance(row, dict) or row.get("resolution_status") != "resolved":
            continue
        fid, nid = str(row.get("fantrax_player_id") or ""), str(row.get("nhl_player_id") or "")
        if fid and nid.isdigit() and _normalize_text(row.get("canonical_player_name") or row.get("fantrax_player_name")):
            result[fid] = row
    return result


def _apply_verified_history(current: dict[str, Any], old: dict[str, Any] | None) -> dict[str, Any]:
    if old is None:
        return current
    if _normalize_text(current.get("canonical_player_name")) != _normalize_text(old.get("canonical_player_name") or old.get("fantrax_player_name")):
        # A permanent NHL ID may survive a legitimate name change, but a
        # reused Fantrax ID cannot silently acquire a different NHL identity.
        # Current NHL evidence corroborating the same permanent NHL ID is
        # sufficient; otherwise both possibilities stay under review.
        if (current.get("resolution_status") == "resolved" and
            str(current.get("nhl_player_id") or "") == str(old.get("nhl_player_id") or "")):
            current.setdefault("evidence", []).append("Provider name changed; current and prior authoritative NHL IDs agree.")
            return current
        current.update(resolution_status="ambiguous", match_confidence=0.0,
                       nhl_player_id="", match_method="fantrax_id_name_conflict")
        current.setdefault("evidence", []).append("Prior verified name differs from current provider name; no common NHL ID established.")
        return current
    old_id = str(old.get("nhl_player_id") or "")
    new_id = str(current.get("nhl_player_id") or "")
    if current.get("resolution_status") == "resolved":
        if new_id != old_id:
            current.update(resolution_status="ambiguous", match_confidence=0.0,
                           nhl_player_id="", match_method="conflicting_verified_identity")
            current.setdefault("evidence", []).append("Prior verified NHL identity disagrees with current match; review required.")
        return current
    if current.get("resolution_status") not in ("unresolved", "review", "ambiguous"):
        return current
    # Only preserve a historical link where there is no contradictory current
    # NHL candidate. An ambiguous candidate list that excludes the previously
    # verified NHL ID is positive contrary evidence, not an absence of data.
    if new_id and new_id != old_id:
        return current
    candidate_ids = {str(cid) for cid in current.get("candidate_nhl_ids") or []}
    if candidate_ids and old_id not in candidate_ids:
        return current
    saved = dict(current)
    for key in ("nhl_player_id", "nhl_player_name", "nhl_team", "nhl_position"):
        saved[key] = old.get(key, "")
    saved.update(resolution_status="resolved", match_confidence=max(0.95, float(old.get("match_confidence") or 0.0)),
                 match_method="preserved_verified_identity")
    saved["evidence"] = list(current.get("evidence") or []) + ["Verified persistent Fantrax/NHL ID link preserved; club is temporal context."]
    return saved


def _block_duplicate_nhl_assignments(rows: list[dict[str, Any]]) -> None:
    by_nhl_id: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if row.get("resolution_status") == "resolved" and row.get("nhl_player_id"):
            by_nhl_id.setdefault(str(row["nhl_player_id"]), []).append(row)
    for same_player in by_nhl_id.values():
        if len({row["fantrax_player_id"] for row in same_player}) > 1:
            for row in same_player:
                row["resolution_status"] = "ambiguous"
                row["match_confidence"] = 0.0
                row["match_method"] = "duplicate_nhl_identity_conflict"
                row["nhl_player_id"] = ""
                row.setdefault("evidence", []).append("NHL ID assigned to multiple Fantrax players; manual verification required.")


def _validated_historical_rosters(root: Path):
    """Only ingest structurally verified archives; no historical-owner inference."""
    if not root.is_dir():
        return
    for path in sorted(root.glob('*/*/period_*.json')):
        try:
            payload = read_json(path)
            if (not isinstance(payload, dict) or payload.get("verified") is not True or
                payload.get("schema") != "athena.fantrax_period_rosters.v1" or
                payload.get("league_id") != path.parent.parent.name or
                str(payload.get("season")) != path.parent.name or
                path.stem != f"period_{int(payload['period']):03d}" or
                not isinstance(payload.get("records"), list) or not payload["records"]):
                continue
            rows = payload["records"]
            ids = [str(p.get("player_id") or "") for p in rows if isinstance(p, dict)]
            if len(ids) != len(rows) or not all(re.fullmatch(r"[A-Za-z0-9]+", x) for x in ids) or len(set(ids)) != len(ids):
                continue
            teams = payload.get("teams")
            if (not isinstance(teams, list) or not teams or
                payload.get("team_count") != len(teams) or
                payload.get("player_count") != len(rows)):
                continue
            team_ids = {t.get("team_id") for t in teams if isinstance(t, dict)}
            if len(team_ids) != len(teams) or not all(isinstance(t, str) and t for t in team_ids):
                continue
            if any(not isinstance(p.get("position"), str) or not p["position"] or
                   p.get("owner_team_id") not in team_ids or
                   p.get("roster_status") not in ("ACTIVE", "RESERVE", "INJURED_RESERVE") or
                   p.get("active_for_period") is not (p.get("roster_status") == "ACTIVE")
                   for p in rows):
                continue
            yield payload
        except (OSError, KeyError, TypeError, ValueError):
            continue


def _historical_transaction_candidates(payload: Any) -> dict[str, list[dict[str, str]]]:
    """Extract *named* Fantrax scorer identities from transaction evidence.

    This is identity metadata only. A transaction is not evidence of roster
    eligibility, credit, or an NHL organization at historical game time.
    """
    collected: dict[str, list[dict[str, str]]] = defaultdict(list)
    def scan(node: Any):
        if isinstance(node, dict):
            scorer = node.get("scorer")
            if isinstance(scorer, dict):
                fid = _safe_str(scorer.get("scorerId") or scorer.get("id"))
                name = _fantrax_display_name(scorer.get("name"))
                if (re.fullmatch(r"[A-Za-z0-9]+", fid) and name and
                    _normalize_text(name) and not name.isnumeric()):
                    collected[fid].append({"player_id": fid, "player_name": name,
                        "nhl_team": "", "position": _safe_str(scorer.get("posShortNames")),
                        "source": "fantrax_transaction_scorer"})
            for k,v in node.items():
                if k != "scorer":
                    scan(v)
        elif isinstance(node, list):
            for element in node:
                scan(element)
    scan(payload)
    return collected


def collect_identity_population(current_players: list[dict[str, Any]], previous_rows: Any,
                                *, archives_root: Path, transactions: Any) -> tuple[list[dict[str, Any]], set[str]]:
    """Resolve current and historical Fantrax IDs against the SAME NHL universe.

    A historical archive typically has no player name. When the provider name
    cannot be recovered from transactions or earlier map observations, retain
    a clearly unresolved ID rather than assign it by position or NHL stats.
    """
    current_by_id = {str(p.get("player_id") or p.get("fantrax_player_id")): p
                     for p in current_players}
    prior_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if isinstance(previous_rows, list):
        for row in previous_rows:
            if isinstance(row, dict):
                fid = _safe_str(row.get("fantrax_player_id"))
                if re.fullmatch(r"[A-Za-z0-9_-]+", fid):
                    name = _safe_str(row.get("canonical_player_name") or row.get("fantrax_player_name"))
                    if name:
                        prior_by_id[fid].append({"player_id": fid,"player_name": name,
                            "nhl_team": _safe_str(row.get("fantrax_nhl_team")),
                            "position": _safe_str(row.get("fantrax_position")),
                            "source": "prior_identity_registry"})
    tx_by_id = _historical_transaction_candidates(transactions)
    archive_by_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    for archive in _validated_historical_rosters(archives_root):
        for row in archive["records"]:
            fid = str(row["player_id"])
            archive_by_id[fid].append({"player_id":fid, "player_name": _safe_str(row.get("player_name")),
                "nhl_team": "", "position": _safe_str(row.get("position")),
                "source": f"archived_period_{archive['season']}_{archive['period']}"})

    # Transaction events and old non-resolved registry entries survive a
    # dropped player's departure. The archive-only pool covers any player
    # never encountered by one of those named metadata sources.
    universe = set(current_by_id) | set(prior_by_id) | set(tx_by_id) | set(archive_by_id)
    population = []
    for fid in sorted(universe):
        if fid in current_by_id:
            record = dict(current_by_id[fid])
            record["identity_sources"] = ["current_player_master"]
            population.append(record)
            continue
        evidence = archive_by_id.get(fid, []) + tx_by_id.get(fid, []) + prior_by_id.get(fid, [])
        names = {_normalize_text(row.get("player_name")) for row in evidence if row.get("player_name")}
        names.discard("")
        # Do not silently merge two conflicting names attached to one provider
        # ID; that could be a provider change, bad export, or ID reuse.
        inconsistent = len(names) > 1
        preferred = next((row for row in evidence if _normalize_text(row.get("player_name"))), None)
        name = preferred["player_name"] if preferred is not None else ""
        positions = [row.get("position", "") for row in evidence if row.get("position")]
        position = positions[0] if positions else ""
        record = {"player_id": fid,"player_name": name, "nhl_team": "",
                  "position": position, "identity_sources": sorted({row["source"] for row in evidence}),
                  "historical_identity": True}
        if inconsistent:
            record["identity_source_conflict"] = sorted(names)
        population.append(record)
    return population, set(archive_by_id)


def summarize_identity_coverage(identity_rows: list[dict[str, Any]], *,
                                current_ids: set[str], archives_root: Path | None = None) -> dict:
    """Report identity coverage for current and archived rosters without guessing.

    Archived rosters often contain dropped players absent from the current
    player master. Those IDs are tracked, not assigned a fabricated NHL ID.
    """
    by_id = {str(row.get("fantrax_player_id")): row for row in identity_rows
             if isinstance(row, dict) and row.get("fantrax_player_id")}

    def explain(fid: str) -> dict:
        row = by_id.get(fid)
        status = row.get("resolution_status") if row else "not_in_identity_map"
        return {
            "fantrax_player_id": fid,
            "player_name": (row.get("canonical_player_name") or row.get("fantrax_player_name") or "") if row else "",
            "resolution_status": status,
            "cause": ("identity_missing_from_registry" if row is None else
                      "ambiguous_nhl_match" if status == "ambiguous" else
                      "not_verified_against_nhl_candidates" if status in ("unresolved", "review") else
                      "verified"),
            "on_current_roster": fid in current_ids,
            "match_method": row.get("match_method", "not_indexed") if row else "not_indexed",
            "identity_sources": row.get("identity_sources", []) if row else [],
            "candidate_nhl_player_id": row.get("nhl_player_id", "") if row else "",
        }

    current_unknown = [explain(fid) for fid in sorted(current_ids)
                       if by_id.get(fid, {}).get("resolution_status") != "resolved"]
    out = {"schema":"athena.player_identity_coverage.v1",
           "current_roster_count": len(current_ids),
           "current_resolved_count": len(current_ids)-len(current_unknown),
           "current_unverified": current_unknown,
           "historical_periods": {},
           "interpretation": "Identity coverage only; no inference of historical ownership, NHL debut, or credited fantasy points"}
    if archives_root is not None and archives_root.is_dir():
        # Period-roster archives have a provider period echo and were validated
        # when written. Recheck identity and basic structural consistency before
        # reporting a period as indexed; an invalid cache is not evidence.
        for payload in _validated_historical_rosters(archives_root):
            try:
                rows = payload["records"]
                ids = [str(p.get("player_id") or "") for p in rows if isinstance(p, dict)]
                if not ids or len(ids) != len(rows) or len(set(ids)) != len(ids) or not all(ids):
                    continue
                active = [row for row in rows if row.get("roster_status") == "ACTIVE" and row.get("active_for_period") is True]
                other = [row for row in rows if row.get("roster_status") in ("RESERVE", "INJURED_RESERVE") and row.get("active_for_period") is False]
                if len(active)+len(other) != len(rows):
                    continue
                outstanding = [explain(str(row["player_id"])) for row in active
                               if by_id.get(str(row["player_id"]), {}).get("resolution_status") != "resolved"]
                key = f"{payload['league_id']}/{payload['season']}/{payload['period']}"
                out['historical_periods'][key] = {
                    'league_id': payload['league_id'], 'season': payload['season'], 'period': payload['period'],
                    'active_count': len(active), 'active_resolved': len(active)-len(outstanding),
                    'unverified_active': outstanding,
                    'reserve_count': len(other), 'eligibility': 'period_snapshot_only_not_game_effective',
                }
            except (ValueError, TypeError, KeyError, OSError):
                continue
    out['historical_periods_with_gaps'] = sum(bool(x['unverified_active']) for x in out['historical_periods'].values())
    return out


def build_player_identity_map() -> list[dict[str, Any]]:
    log_header("Player Identity Resolver")

    player_master = read_json(PLAYER_MASTER_PATH)
    nhl_payload = read_json(NHL_SKATER_SUMMARY_PATH) if NHL_SKATER_SUMMARY_PATH.exists() else None
    supplementary = read_json(NHL_IDENTITY_CANDIDATES_PATH) if NHL_IDENTITY_CANDIDATES_PATH.exists() else None
    previous_rows = read_json(OUTPUT_JSON) if OUTPUT_JSON.exists() else []

    if not isinstance(player_master, list) or not player_master:
        raise ValueError("Output/player_master.json must contain current player records.")
    master_ids = [str(p.get("player_id") or p.get("fantrax_player_id") or "")
                  for p in player_master if isinstance(p, dict)]
    if len(master_ids) != len(player_master) or not all(master_ids) or len(set(master_ids)) != len(master_ids):
        raise ValueError("Current Fantrax player master has missing or duplicate player IDs")

    nhl_rows = _extract_nhl_rows(nhl_payload) + _extract_nhl_rows(supplementary)
    nhl_candidates = _build_nhl_candidates(nhl_rows)
    previous_verified = _prior_verified_by_id(previous_rows)
    if not nhl_candidates and not previous_verified:
        raise ValueError("Neither NHL candidates nor durable verified identity history are available")

    # Keep input roots aligned with the active output, including isolated
    # test/workspace roots that override only the canonical file paths.
    transaction_source = (FANTRAX_TRANSACTION_SOURCE_PATH if OUTPUT_JSON.parent == OUTPUT_DIR
                          else NHL_SKATER_SUMMARY_PATH.parent / "transactions.json")
    archives_root = (FANTRAX_PERIOD_ROSTERS_DIR if OUTPUT_JSON.parent == OUTPUT_DIR
                     else OUTPUT_JSON.parent / "PeriodRosters")
    transactions = (read_json(transaction_source) if transaction_source.exists() else None)
    population, archived_ids = collect_identity_population(
        player_master, previous_rows, archives_root=archives_root, transactions=transactions)

    name_index: dict[str, list[dict[str, Any]]] = {}
    for candidate in nhl_candidates:
        for alias in candidate.get("normalized_aliases", [candidate["normalized_name"]]):
            name_index.setdefault(alias, []).append(candidate)

    identity_rows = []
    for player in population:
        current = _match_player(player, nhl_candidates, name_index)
        current["identity_sources"] = player.get("identity_sources", [])
        if player.get("historical_identity"):
            current["historical_identity"] = True
        if player.get("identity_source_conflict"):
            current.update(resolution_status="ambiguous", nhl_player_id="", match_confidence=0.0,
                           match_method="conflicting_fantrax_identity_names")
            current["evidence"] = ["Conflicting Fantrax names for the same player ID; identity requires review."]
        elif not _normalize_text(player.get("player_name")):
            current.update(resolution_status="unresolved", nhl_player_id="", match_confidence=0.0,
                           match_method="missing_historical_fantrax_name")
            current["evidence"] = ["Historical Fantrax ID has no verified name in available provider sources."]
        else:
            current = _apply_verified_history(current, previous_verified.get(current["fantrax_player_id"]))
            if (player.get("historical_identity") and
                current.get("match_method") == "preserved_verified_identity"):
                current["match_method"] = "preserved_historical_identity"
        identity_rows.append(current)
    _block_duplicate_nhl_assignments(identity_rows)
    identity_rows.sort(key=lambda row: (row.get("resolution_status", ""),
                                         row.get("canonical_player_name", ""),
                                         row.get("fantrax_player_id", "")))

    write_json(OUTPUT_JSON, identity_rows)
    _write_csv(OUTPUT_CSV, identity_rows)
    coverage = summarize_identity_coverage(identity_rows, current_ids=set(master_ids),
                                           archives_root=archives_root)
    write_json(OUTPUT_JSON.parent / "player_identity_coverage.json", coverage)

    resolved = sum(1 for row in identity_rows if row.get("resolution_status") == "resolved")
    review = sum(1 for row in identity_rows if row.get("resolution_status") == "review")
    ambiguous = sum(1 for row in identity_rows if row.get("resolution_status") == "ambiguous")
    unresolved = sum(1 for row in identity_rows if row.get("resolution_status") == "unresolved")
    avg_confidence = (sum(float(row.get("match_confidence") or 0.0) for row in identity_rows) / len(identity_rows)
                      if identity_rows else 0.0)
    log(f"Current Fantrax Players: {len(player_master)}")
    log(f"NHL Candidate Identities: {len(nhl_candidates)}")
    log(f"Historical Identity Population: {len([x for x in identity_rows if x['fantrax_player_id'] not in set(master_ids)])}; archived IDs: {len(archived_ids)}")
    log(f"Resolved: {resolved}; Review: {review}; Ambiguous: {ambiguous}; Unresolved: {unresolved}")
    log(f"Average Match Confidence: {round(avg_confidence, 3)}")
    log_section("Output Files")
    log(f"JSON: {OUTPUT_JSON}")
    log(f"CSV: {OUTPUT_CSV}")
    log("Completed successfully.")
    return identity_rows


if __name__ == "__main__":
    build_player_identity_map()
