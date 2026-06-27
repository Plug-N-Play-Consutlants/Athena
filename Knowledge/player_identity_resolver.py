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
    candidates: list[dict[str, Any]] = []
    for row in rows:
        name = _extract_nhl_player_name(row)
        player_id = _extract_nhl_player_id(row)
        team = _extract_nhl_team(row)
        position = _extract_nhl_position(row)

        if not name or not player_id:
            continue

        candidates.append(
            {
                "nhl_player_id": player_id,
                "nhl_player_name": name,
                "nhl_team": team,
                "nhl_position": position,
                "normalized_name": _normalize_text(name),
                "raw": row,
            }
        )
    return candidates


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
        same_team = [row for row in exact_name_matches if row.get("nhl_team") == fantrax_team and fantrax_team]
        if len(same_team) == 1:
            return _resolved(base, same_team[0], 0.99, "exact_name_and_team")

        same_position = [
            row for row in exact_name_matches if row.get("nhl_position") == fantrax_position and fantrax_position
        ]
        if len(exact_name_matches) == 1:
            match = exact_name_matches[0]
            confidence = 0.94 if match.get("nhl_team") else 0.92
            method = "unique_exact_name"
            if fantrax_team and match.get("nhl_team") and match.get("nhl_team") != fantrax_team:
                confidence = 0.86
                method = "unique_exact_name_team_mismatch"
            return _resolved(base, match, confidence, method)

        if len(same_position) == 1:
            return _resolved(base, same_position[0], 0.88, "exact_name_and_position_ambiguous_team")

        return _ambiguous(base, exact_name_matches, "multiple_exact_name_matches")

    # Fuzzy fallback, weighted toward same NHL team. This is intentionally conservative.
    scored: list[tuple[float, dict[str, Any]]] = []
    for candidate in nhl_candidates:
        ratio = SequenceMatcher(None, fantrax_name_key, candidate["normalized_name"]).ratio()
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


def build_player_identity_map() -> list[dict[str, Any]]:
    log_header("Player Identity Resolver")

    player_master = read_json(PLAYER_MASTER_PATH)
    nhl_payload = read_json(NHL_SKATER_SUMMARY_PATH)

    if not isinstance(player_master, list):
        raise ValueError("Output/player_master.json must contain a list of players.")

    nhl_rows = _extract_nhl_rows(nhl_payload)
    nhl_candidates = _build_nhl_candidates(nhl_rows)

    name_index: dict[str, list[dict[str, Any]]] = {}
    for candidate in nhl_candidates:
        name_index.setdefault(candidate["normalized_name"], []).append(candidate)

    identity_rows = [
        _match_player(player, nhl_candidates, name_index)
        for player in player_master
        if isinstance(player, dict)
    ]

    identity_rows.sort(
        key=lambda row: (
            row.get("resolution_status", ""),
            row.get("canonical_player_name", ""),
            row.get("fantrax_player_id", ""),
        )
    )

    write_json(OUTPUT_JSON, identity_rows)
    _write_csv(OUTPUT_CSV, identity_rows)

    resolved = sum(1 for row in identity_rows if row.get("resolution_status") == "resolved")
    review = sum(1 for row in identity_rows if row.get("resolution_status") == "review")
    ambiguous = sum(1 for row in identity_rows if row.get("resolution_status") == "ambiguous")
    unresolved = sum(1 for row in identity_rows if row.get("resolution_status") == "unresolved")
    avg_confidence = (
        sum(float(row.get("match_confidence") or 0.0) for row in identity_rows) / len(identity_rows)
        if identity_rows
        else 0.0
    )

    log(f"Fantrax Players: {len(player_master)}")
    log(f"NHL Candidate Rows: {len(nhl_candidates)}")
    log(f"Resolved: {resolved}")
    log(f"Review: {review}")
    log(f"Ambiguous: {ambiguous}")
    log(f"Unresolved: {unresolved}")
    log(f"Average Match Confidence: {round(avg_confidence, 3)}")

    log_section("Output Files")
    log(f"JSON: {OUTPUT_JSON}")
    log(f"CSV: {OUTPUT_CSV}")
    log("Completed successfully.")

    return identity_rows


if __name__ == "__main__":
    build_player_identity_map()
