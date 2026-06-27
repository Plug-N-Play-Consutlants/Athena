"""Athena Player Intelligence Foundation.

This module evaluates a canonical player entity using existing Athena outputs.
It does not fetch provider data and it does not invent missing evidence.

Input evidence can come from public NHL outputs and fantasy provider outputs.
The same evaluation object shape is used in public and fantasy contexts.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
import re
import unicodedata
from difflib import SequenceMatcher

from Core.json_utils import read_optional_json, write_json
from Core.project_paths import OUTPUT_DIR, REPORTS_DIR

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in ("default", "en", "value", "name"):
            if key in value:
                return _safe_str(value.get(key))
        return ""
    return str(value).strip()


def _display_name(value: Any) -> str:
    name = _safe_str(value)
    if "," in name:
        last, first = [part.strip() for part in name.split(",", 1)]
        if first and last:
            return f"{first} {last}"
    return name


def normalize_name(value: Any) -> str:
    text = _display_name(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace(".", " ").replace("-", " ").replace("'", "")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _rows(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("records", "players", "data", "items", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    return []


def _read_output(filename: str, project_root: Path = PROJECT_ROOT) -> Any:
    return read_optional_json(project_root / "Output" / filename)


def _player_identity(row: Dict[str, Any], name_fields: List[str]) -> tuple[str, str, str, str]:
    name = ""
    for field in name_fields:
        name = _display_name(row.get(field))
        if name:
            break
    player_id = _safe_str(row.get("player_id") or row.get("fantrax_player_id") or row.get("asset_id") or row.get("nhl_player_id"))
    team = _safe_str(row.get("nhl_team") or row.get("team") or row.get("pro_team"))
    position = _safe_str(row.get("position") or row.get("eligible_position") or row.get("eligiblePos"))
    return player_id, name, team, position


def _unique_player_rows(rows: List[Dict[str, Any]], name_fields: List[str]) -> List[Dict[str, Any]]:
    seen = set()
    unique = []
    for row in rows:
        identity = _player_identity(row, name_fields)
        key = identity if any(identity) else tuple(sorted((str(k), str(v)) for k, v in row.items())[:6])
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def _ambiguity_row(query: str, matches: List[Dict[str, Any]], name_fields: List[str], reason: str) -> Dict[str, Any]:
    return {
        "__ambiguous_player_match": True,
        "query": query,
        "reason": reason,
        "matches": _unique_player_rows(matches, name_fields)[:6],
        "name_fields": name_fields,
    }


def _find_player(query: str, rows: List[Dict[str, Any]], name_fields: List[str]) -> Optional[Dict[str, Any]]:
    key = normalize_name(query)
    if not key:
        return None

    # Exact normalized display-name match first. If there are multiple real
    # identities with the same name (for example Sebastian Aho), return an
    # ambiguity object instead of silently choosing one.
    exact_matches: List[Dict[str, Any]] = []
    for row in rows:
        for field in name_fields:
            if normalize_name(row.get(field)) == key:
                exact_matches.append(row)
                break
    exact_matches = _unique_player_rows(exact_matches, name_fields)
    if len(exact_matches) == 1:
        return exact_matches[0]
    if len(exact_matches) > 1:
        return _ambiguity_row(query, exact_matches, name_fields, "multiple_exact_name_matches")

    # Then contains match for natural prompts like "Tell me about Sidney Crosby".
    contains_matches: List[Dict[str, Any]] = []
    for row in rows:
        for field in name_fields:
            n = normalize_name(row.get(field))
            if n and (n in key or key in n):
                contains_matches.append(row)
                break
    contains_matches = _unique_player_rows(contains_matches, name_fields)
    if len(contains_matches) == 1:
        return contains_matches[0]
    if len(contains_matches) > 1:
        return _ambiguity_row(query, contains_matches, name_fields, "multiple_partial_name_matches")

    # Token overlap + edit-distance fallback, still bounded. This allows simple
    # spelling mistakes such as "Austin Mathtwes" to resolve to Auston Matthews
    # without allowing random text to become an invented player match.
    qtokens = set(key.split())
    scored: List[tuple[float, Dict[str, Any]]] = []
    for row in rows:
        best_for_row = 0.0
        for field in name_fields:
            n = normalize_name(row.get(field))
            if not n:
                continue
            ntokens = set(n.split())
            token_score = len(qtokens & ntokens) / max(len(ntokens), len(qtokens), 1)
            edit_score = SequenceMatcher(None, key, n).ratio()
            score = max(token_score, edit_score)
            best_for_row = max(best_for_row, score)
        if best_for_row >= 0.72:
            scored.append((best_for_row, row))
    if not scored:
        return None
    scored.sort(key=lambda item: item[0], reverse=True)
    top_score = scored[0][0]
    top = _unique_player_rows([row for score, row in scored if abs(score - top_score) <= 0.025], name_fields)
    if len(top) == 1 and top_score >= 0.78:
        return top[0]
    if top_score >= 0.72:
        return _ambiguity_row(query, [row for _, row in scored[:6]], name_fields, "fuzzy_match_requires_review")
    return None


def _index_by_id(rows: List[Dict[str, Any]], fields: List[str]) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        for field in fields:
            val = _safe_str(row.get(field))
            if val and val not in index:
                index[val] = row
    return index


def _index_by_name(rows: List[Dict[str, Any]], fields: List[str]) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        for field in fields:
            key = normalize_name(row.get(field))
            if key and key not in index:
                index[key] = row
    return index


def _lookup_related(base: Dict[str, Any], rows: List[Dict[str, Any]], id_fields: List[str], name_fields: List[str]) -> Optional[Dict[str, Any]]:
    ids = []
    for f in ("player_id", "fantrax_player_id", "asset_id", "nhl_player_id"):
        v = _safe_str(base.get(f))
        if v:
            ids.append(v)
    by_id = _index_by_id(rows, id_fields)
    for v in ids:
        if v in by_id:
            return by_id[v]
    by_name = _index_by_name(rows, name_fields)
    for f in ("player_name", "nhl_player_name", "canonical_player_name"):
        key = normalize_name(base.get(f))
        if key in by_name:
            return by_name[key]
    return None


def _to_float(value: Any) -> Optional[float]:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def _band_from_percentile(percentile: Optional[float]) -> str:
    if percentile is None:
        return "unknown"
    if percentile >= 0.90:
        return "elite"
    if percentile >= 0.75:
        return "top_tier"
    if percentile >= 0.55:
        return "above_average"
    if percentile >= 0.35:
        return "middle_tier"
    return "below_average"


def _trajectory(points_per_game: Optional[float], percentile: Optional[float]) -> str:
    if percentile is None and points_per_game is None:
        return "insufficient_evidence"
    if percentile is not None and percentile >= 0.90:
        return "high_impact_current_production"
    if points_per_game is not None and points_per_game >= 1.0:
        return "strong_current_production"
    if percentile is not None and percentile >= 0.55:
        return "useful_current_production"
    return "limited_current_production"


def _confidence(evidence: Dict[str, Any], mode: str) -> float:
    weights = {
        "identity": 0.20,
        "production": 0.30,
        "fantasy": 0.20 if mode == "fantasy" else 0.0,
        "contract": 0.15 if mode == "fantasy" else 0.0,
        "status": 0.15 if mode == "fantasy" else 0.10,
    }
    total = sum(weights.values()) or 1.0
    score = 0.0
    for key, weight in weights.items():
        if evidence.get(key):
            score += weight
    return round(min(max(score / total, 0.05), 0.95), 2)


def evaluate_player(query: str, mode: str = "fantasy", project_root: Path = PROJECT_ROOT) -> Dict[str, Any]:
    mode = (mode or "fantasy").strip().lower()
    player_master = _rows(_read_output("player_master.json", project_root))
    player_profiles = _rows(_read_output("player_profiles.json", project_root))
    player_production = _rows(_read_output("player_production.json", project_root))
    player_contracts = _rows(_read_output("player_contracts.json", project_root))
    player_status = _rows(_read_output("player_status.json", project_root))
    player_identity_map = _rows(_read_output("player_identity_map.json", project_root))

    base = _find_player(query, player_master, ["player_name", "nhl_player_name", "canonical_player_name"])
    if base is None:
        base = _find_player(query, player_profiles, ["player_name", "nhl_player_name", "canonical_player_name"])
    if base is None:
        base = _find_player(query, player_production, ["player_name", "nhl_player_name"])

    if isinstance(base, dict) and base.get("__ambiguous_player_match"):
        matches = base.get("matches") or []
        observed = []
        cards = []
        for match in matches:
            _, match_name, match_team, match_pos = _player_identity(match, base.get("name_fields") or ["player_name", "nhl_player_name", "canonical_player_name"])
            label = match_name or "Unknown player"
            detail = " / ".join([part for part in [match_pos, match_team] if part]) or "needs more detail"
            observed.append(f"Possible match: {label} ({detail}).")
            cards.append({"label": label, "value": detail})
        return {
            "intent": "player_disambiguation",
            "entity_type": "player",
            "query": query,
            "status": "ambiguous",
            "title": "Which player do you mean?",
            "confidence": 0.42,
            "evaluation": "Athena found more than one plausible player match. Add a team, position, or more context so Scout does not merge distinct players.",
            "evidence": {"matches": matches},
            "observed_facts": observed or ["Multiple possible player identities were found."],
            "limitations": ["Player identity is intentionally not name-only. Ambiguous names require disambiguation."],
            "cards": cards,
            "developer": {
                "mode": mode,
                "files_read": ["Output/player_master.json", "Output/player_profiles.json", "Output/player_production.json"],
                "missing": ["player_disambiguation_selection"],
                "match_reason": base.get("reason"),
            },
        }

    if base is None:
        return {
            "intent": "player_analysis",
            "entity_type": "player",
            "query": query,
            "status": "no_match",
            "title": "Player intelligence unavailable",
            "confidence": 0.15,
            "evaluation": "Athena could not match this question to a player in the current player evidence outputs.",
            "evidence": {},
            "observed_facts": ["No canonical player match was found."],
            "limitations": ["Run player identity/production builders or ask about a player present in the current outputs."],
            "developer": {
                "mode": mode,
                "files_read": ["Output/player_master.json", "Output/player_profiles.json", "Output/player_production.json"],
                "missing": ["canonical_player_match"],
            },
        }

    profile = _lookup_related(base, player_profiles, ["player_id", "asset_id", "fantrax_player_id"], ["player_name", "nhl_player_name"])
    production = _lookup_related(base, player_production, ["player_id", "nhl_player_id", "fantrax_player_id"], ["player_name", "nhl_player_name"])
    contract = _lookup_related(base, player_contracts, ["player_id", "fantrax_player_id", "asset_id"], ["player_name"])
    status = _lookup_related(base, player_status, ["player_id", "fantrax_player_id", "asset_id"], ["player_name"])
    identity = _lookup_related(base, player_identity_map, ["player_id", "fantrax_player_id", "nhl_player_id"], ["fantrax_player_name", "nhl_player_name", "canonical_player_name"])

    display = _display_name(
        (production or {}).get("nhl_player_name")
        or (base or {}).get("player_name")
        or (profile or {}).get("player_name")
        or query
    )
    position = _safe_str((production or {}).get("position") or base.get("position") or (profile or {}).get("position"))
    nhl_team = _safe_str((production or {}).get("nhl_team") or base.get("nhl_team") or (profile or {}).get("nhl_team"))
    fantasy_team = _safe_str((profile or {}).get("fantasy_team") or base.get("owner_team") or (contract or {}).get("fantasy_team") or (status or {}).get("fantasy_team"))

    ppg = _to_float((production or {}).get("points_per_game"))
    points = _to_float((production or {}).get("points"))
    goals = _to_float((production or {}).get("goals"))
    assists = _to_float((production or {}).get("assists"))
    games = _to_float((production or {}).get("games_played"))
    percentile = _to_float((production or {}).get("production_percentile"))
    production_band = _band_from_percentile(percentile)

    evidence_presence = {
        "identity": bool(base or identity),
        "production": bool(production),
        "fantasy": bool(profile),
        "contract": bool(contract),
        "status": bool(status),
    }
    confidence = _confidence(evidence_presence, mode)

    observed: List[str] = []
    observed.append(f"Identity: {display}" + (f", {position}" if position else "") + (f", {nhl_team}" if nhl_team else "") + ".")
    if production:
        observed.append(f"Production: {int(points or 0)} points in {int(games or 0)} games ({ppg:.3f} points/game)." if ppg is not None else f"Production points: {points}.")
        observed.append(f"Goal/assist split: {int(goals or 0)} goals, {int(assists or 0)} assists.")
        observed.append(f"Production band: {production_band}.")
    else:
        observed.append("Production evidence is not available for this player in current outputs.")
    if mode == "fantasy":
        if fantasy_team:
            observed.append(f"Fantasy context: rostered by {fantasy_team}.")
        if contract:
            observed.append(f"Contract context: {contract.get('contract_band', contract.get('contract_status', 'unknown'))}, years remaining {contract.get('years_remaining', contract.get('contract_years_remaining', 'unknown'))}.")
        if status:
            observed.append(f"Availability status: {status.get('availability_status', 'unknown')} ({status.get('roster_slot', 'unknown')}).")

    limitations: List[str] = []
    if not production:
        limitations.append("Public NHL production evidence is missing for this player.")
    if mode == "fantasy" and not profile:
        limitations.append("Fantasy profile evidence is missing for this player.")
    if mode == "fantasy" and not contract:
        limitations.append("Contract evidence is missing or not normalized for this player.")
    limitations.append("Player Intelligence 4B.1 does not yet evaluate line deployment, power-play role, injuries, schedule strength, or future projection curves.")

    trajectory = _trajectory(ppg, percentile)
    if production and production_band in ("elite", "top_tier"):
        evaluation = f"{display} profiles as a {production_band.replace('_', ' ')} producer in the current public production evidence."
    elif production:
        evaluation = f"{display} has usable production evidence and currently profiles as {production_band.replace('_', ' ')} by production percentile."
    else:
        evaluation = f"Athena can identify {display}, but does not yet have enough production evidence for a meaningful player evaluation."

    if mode == "fantasy" and fantasy_team:
        evaluation += f" In fantasy context, he is currently associated with {fantasy_team}."

    result = {
        "intent": "player_analysis",
        "entity_type": "player",
        "query": query,
        "status": "available",
        "title": f"Player intelligence: {display}",
        "confidence": confidence,
        "evaluation": evaluation,
        "player": {
            "name": display,
            "position": position,
            "nhl_team": nhl_team,
            "fantasy_team": fantasy_team,
            "player_id": _safe_str(base.get("player_id") or base.get("fantrax_player_id") or (profile or {}).get("player_id")),
            "nhl_player_id": _safe_str((production or {}).get("nhl_player_id") or (identity or {}).get("nhl_player_id")),
        },
        "profiles": {
            "identity": {"available": evidence_presence["identity"], "source": "player_master/player_identity_map"},
            "production": {
                "available": bool(production),
                "points": points,
                "goals": goals,
                "assists": assists,
                "games_played": games,
                "points_per_game": ppg,
                "production_percentile": percentile,
                "production_band": production_band,
                "source": (production or {}).get("source", "player_production"),
            },
            "fantasy": {
                "available": bool(profile),
                "fantasy_team": fantasy_team,
                "position_scarcity_ratio": (profile or {}).get("position_scarcity_ratio"),
                "keeper_relevance": (profile or {}).get("keeper_relevance"),
                "evidence_completeness": (profile or {}).get("evidence_completeness"),
            },
            "contract": {
                "available": bool(contract),
                "contract_band": (contract or {}).get("contract_band") or (contract or {}).get("contract_status"),
                "years_remaining": (contract or {}).get("years_remaining") or (contract or {}).get("contract_years_remaining"),
            },
            "availability": {
                "available": bool(status),
                "availability_status": (status or {}).get("availability_status"),
                "roster_slot": (status or {}).get("roster_slot"),
            },
            "trajectory": {
                "available": bool(production),
                "classification": trajectory,
            },
        },
        "observed_facts": observed,
        "limitations": limitations,
        "evidence_presence": evidence_presence,
        "developer": {
            "mode": mode,
            "files_read": [
                "Output/player_master.json",
                "Output/player_profiles.json",
                "Output/player_production.json",
                "Output/player_contracts.json",
                "Output/player_status.json",
                "Output/player_identity_map.json",
            ],
            "modules_executed": ["PlayerIntelligence.evaluate_player"],
            "missing": [name for name, present in evidence_presence.items() if not present],
        },
    }
    return result


def build_player_evaluation(query: str, mode: str = "fantasy", project_root: Path = PROJECT_ROOT, write_report: bool = True) -> Dict[str, Any]:
    result = evaluate_player(query, mode=mode, project_root=project_root)
    if write_report:
        safe = re.sub(r"[^a-z0-9]+", "_", normalize_name(query))[:60] or "player"
        out_json = project_root / "Output" / f"player_intelligence_{safe}.json"
        out_txt = project_root / "Reports" / f"player_intelligence_{safe}.txt"
        write_json(out_json, result)
        lines = ["Player Intelligence", "===================", f"Status: {result.get('status')}", f"Title: {result.get('title')}", f"Confidence: {result.get('confidence')}", "", "Evaluation", "----------", str(result.get("evaluation")), "", "Observed Facts", "--------------"]
        lines.extend([f"- {fact}" for fact in result.get("observed_facts", [])])
        lines.extend(["", "Limitations", "-----------"])
        lines.extend([f"- {lim}" for lim in result.get("limitations", [])])
        out_txt.parent.mkdir(parents=True, exist_ok=True)
        out_txt.write_text("\n".join(lines), encoding="utf-8")
        result["reports"] = {"json": str(out_json), "text": str(out_txt)}
    return result
