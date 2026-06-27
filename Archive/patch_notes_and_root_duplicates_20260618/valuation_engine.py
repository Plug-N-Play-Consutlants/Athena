"""
Canonical Valuation Engine.

Consumes canonical Knowledge outputs and produces multi-dimensional player asset
values. This module does not fetch data and does not perform team strategy.

Inputs:
    Output/player_profiles.json
    Output/player_production.json   optional enrichment
    Output/player_bio.json          optional enrichment
    Output/player_contracts.json    optional enrichment
    Output/player_master.json       fallback only
    Output/analysis_profile.json
    Output/league_profile.json

Outputs:
    Output/player_values.json
    Output/player_values.csv
"""

from __future__ import annotations

import csv
from pathlib import Path
from statistics import mean
from typing import Any

from Core.json_utils import read_json, read_optional_json, write_json
from Core.logger import log, log_header, log_section
from Core.project_paths import OUTPUT_DIR


PLAYER_PROFILES_PATH = OUTPUT_DIR / "player_profiles.json"
PLAYER_PRODUCTION_PATH = OUTPUT_DIR / "player_production.json"
PLAYER_BIO_PATH = OUTPUT_DIR / "player_bio.json"
PLAYER_CONTRACTS_PATH = OUTPUT_DIR / "player_contracts.json"
PLAYER_MASTER_FALLBACK_PATH = OUTPUT_DIR / "player_master.json"
ANALYSIS_PROFILE_PATH = OUTPUT_DIR / "analysis_profile.json"
LEAGUE_PROFILE_PATH = OUTPUT_DIR / "league_profile.json"

OUTPUT_JSON = OUTPUT_DIR / "player_values.json"
OUTPUT_CSV = OUTPUT_DIR / "player_values.csv"


VALUATION_DIMENSIONS = [
    "current",
    "future",
    "contract",
    "scarcity",
    "replacement",
    "risk",
    "market",
    "fit",
    "chemistry",
]

BIO_FIELDS_TO_MERGE = [
    "birth_date",
    "age_as_of_date",
    "age_as_of_season_start",
    "birth_city",
    "birth_state_province",
    "birth_country",
    "height_inches",
    "height_centimeters",
    "weight_pounds",
    "weight_kilograms",
    "shoots_catches",
    "sweater_number",
    "is_active",
    "bio_source",
    "bio_evidence_completeness",
]




CONTRACT_FIELDS_TO_MERGE = [
    "contract_years_remaining",
    "max_contract_years",
    "contract_status",
    "contract_score",
    "keeper_eligible",
    "contract_source",
    "contract_evidence_completeness",
]

PRODUCTION_FIELDS_TO_MERGE = [
    "nhl_player_id",
    "nhl_player_name",
    "season",
    "games_played",
    "goals",
    "assists",
    "points",
    "points_per_game",
    "shots",
    "shooting_pct",
    "power_play_goals",
    "power_play_points",
    "short_handed_goals",
    "short_handed_points",
    "even_strength_goals",
    "even_strength_points",
    "time_on_ice_per_game_seconds",
    "current_production_score",
    "production_rank",
    "production_percentile",
    "production_evidence_completeness",
    "production_source",
]


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_float(value: Any, default: float | None = None) -> float | None:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _load_list(path: Path) -> list[dict[str, Any]]:
    payload = read_optional_json(path)
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("players", "records", "data", "items", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    return []


def _load_players() -> tuple[list[dict[str, Any]], str]:
    if PLAYER_PROFILES_PATH.exists():
        data = read_json(PLAYER_PROFILES_PATH)
        if isinstance(data, list):
            return data, "player_profiles"

    data = read_json(PLAYER_MASTER_FALLBACK_PATH)
    if isinstance(data, list):
        return data, "player_master_fallback"

    raise ValueError("No usable player profile or player master data found.")



def _build_bio_lookup() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    rows = _load_list(PLAYER_BIO_PATH)
    by_player_id: dict[str, dict[str, Any]] = {}
    by_nhl_id: dict[str, dict[str, Any]] = {}

    for row in rows:
        player_id = _safe_str(row.get("fantrax_player_id") or row.get("player_id") or row.get("asset_id"))
        nhl_player_id = _safe_str(row.get("nhl_player_id"))
        if player_id:
            by_player_id[player_id] = row
        if nhl_player_id:
            by_nhl_id[nhl_player_id] = row

    return by_player_id, by_nhl_id


def _merge_bio(players: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    bio_by_player_id, bio_by_nhl_id = _build_bio_lookup()
    if not bio_by_player_id and not bio_by_nhl_id:
        return players, 0

    enriched: list[dict[str, Any]] = []
    matched = 0

    for player in players:
        player_id = _safe_str(player.get("player_id") or player.get("asset_id") or player.get("fantrax_player_id"))
        nhl_player_id = _safe_str(player.get("nhl_player_id"))
        bio = bio_by_player_id.get(player_id) or bio_by_nhl_id.get(nhl_player_id)
        merged = dict(player)

        if bio:
            matched += 1
            merged["age"] = bio.get("age_as_of_season_start")
            merged["birth_date"] = bio.get("birth_date")
            merged["bio_source"] = bio.get("bio_source")
            merged["bio_evidence_completeness"] = bio.get("evidence_completeness")
            merged["nhl_player_id"] = merged.get("nhl_player_id") or bio.get("nhl_player_id")
            merged["nhl_team"] = merged.get("nhl_team") or bio.get("nhl_team")
            for field in BIO_FIELDS_TO_MERGE:
                if field not in merged and field in bio:
                    merged[field] = bio.get(field)

        enriched.append(merged)

    return enriched, matched

def _build_production_lookup() -> dict[str, dict[str, Any]]:
    rows = _load_list(PLAYER_PRODUCTION_PATH)
    by_player_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        player_id = _safe_str(row.get("player_id"))
        if not player_id:
            continue
        by_player_id[player_id] = row
    return by_player_id


def _merge_production(players: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    production_by_player_id = _build_production_lookup()
    if not production_by_player_id:
        return players, 0

    enriched: list[dict[str, Any]] = []
    matched = 0
    for player in players:
        player_id = _safe_str(player.get("player_id") or player.get("asset_id"))
        production = production_by_player_id.get(player_id)
        merged = dict(player)
        if production:
            matched += 1
            merged["current_points"] = production.get("points")
            merged["current_goals"] = production.get("goals")
            merged["current_assists"] = production.get("assists")
            merged["games_played"] = production.get("games_played")
            merged["points_per_game"] = production.get("points_per_game")
            merged["current_production_score"] = production.get("current_production_score")
            merged["production_rank"] = production.get("production_rank")
            merged["production_percentile"] = production.get("production_percentile")
            merged["production_source"] = production.get("source")
            merged["production_evidence_completeness"] = production.get("evidence_completeness")
            for field in PRODUCTION_FIELDS_TO_MERGE:
                if field not in merged and field in production:
                    merged[field] = production.get(field)
        enriched.append(merged)
    return enriched, matched



def _build_contract_lookup() -> dict[str, dict[str, Any]]:
    rows = _load_list(PLAYER_CONTRACTS_PATH)
    by_player_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        player_id = _safe_str(row.get("player_id") or row.get("asset_id") or row.get("fantrax_player_id"))
        if not player_id:
            continue
        by_player_id[player_id] = row
    return by_player_id


def _merge_contracts(players: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    contracts_by_player_id = _build_contract_lookup()
    if not contracts_by_player_id:
        return players, 0

    enriched: list[dict[str, Any]] = []
    matched = 0
    for player in players:
        player_id = _safe_str(player.get("player_id") or player.get("asset_id") or player.get("fantrax_player_id"))
        contract = contracts_by_player_id.get(player_id)
        merged = dict(player)

        # player_contracts.py intentionally creates placeholder rows when no
        # contract source exists. Those rows should not be treated as real
        # contract facts. They are useful for audit/template coverage only.
        evidence_completeness = _safe_float((contract or {}).get("evidence_completeness"), 0.0) or 0.0
        has_contract_fact = bool(contract) and evidence_completeness > 0.0

        if has_contract_fact:
            matched += 1
            merged["contract_years_remaining"] = contract.get("contract_years_remaining")
            merged["contract_status"] = contract.get("contract_status")
            merged["contract_score"] = contract.get("contract_score")
            merged["keeper_eligible"] = contract.get("keeper_eligible")
            merged["contract_source"] = contract.get("contract_source")
            merged["contract_evidence_completeness"] = evidence_completeness
            for field in CONTRACT_FIELDS_TO_MERGE:
                if field not in merged and field in contract:
                    merged[field] = contract.get(field)

        enriched.append(merged)
    return enriched, matched


def _weights(analysis_profile: dict[str, Any]) -> dict[str, float]:
    weights = analysis_profile.get("valuation_weights", {})
    if not isinstance(weights, dict):
        weights = analysis_profile.get("weights", {})
    if not isinstance(weights, dict):
        weights = {}

    return {dimension: float(weights.get(dimension, 0.5)) for dimension in VALUATION_DIMENSIONS}


def _fallback_midpoint() -> float:
    return 50.0


def _dimension_value(profile: dict[str, Any], dimension: str) -> tuple[float, list[str], bool]:
    evidence: list[str] = []

    if dimension == "current":
        score = _safe_float(profile.get("current_production_score"))
        if score is not None:
            points = profile.get("current_points") if profile.get("current_points") is not None else profile.get("points")
            ppg = profile.get("points_per_game")
            rank = profile.get("production_rank")
            detail = "Current production score available"
            if points is not None:
                detail += f" from {points} points"
            if ppg is not None:
                detail += f" at {ppg} PPG"
            if rank is not None:
                detail += f"; league production rank {rank}"
            evidence.append(detail + ".")
            return score, evidence, True
        evidence.append("Current production unavailable; using neutral placeholder.")
        return _fallback_midpoint(), evidence, False

    if dimension == "future":
        score = _safe_float(profile.get("future_score"))
        if score is not None:
            evidence.append("Future score available from age/continuity profile.")
            return score, evidence, True

        age = _safe_float(profile.get("age") or profile.get("age_as_of_season_start"))
        production_score = _safe_float(profile.get("current_production_score"))

        if age is not None:
            if age <= 20:
                age_curve_score = 92.0
                age_label = "elite youth/future runway"
            elif age <= 23:
                age_curve_score = 88.0
                age_label = "strong young-prime runway"
            elif age <= 26:
                age_curve_score = 80.0
                age_label = "prime-age future runway"
            elif age <= 29:
                age_curve_score = 70.0
                age_label = "established prime with moderate runway"
            elif age <= 32:
                age_curve_score = 58.0
                age_label = "aging-prime with shorter dynasty runway"
            elif age <= 35:
                age_curve_score = 44.0
                age_label = "late-career dynasty runway risk"
            else:
                age_curve_score = 32.0
                age_label = "significant late-career dynasty runway risk"

            if production_score is not None:
                blended = round((production_score * 0.55) + (age_curve_score * 0.45), 3)
                evidence.append(
                    f"Future value blends current production with age curve: age {age} indicates {age_label}."
                )
                return blended, evidence, True

            evidence.append(f"Future value estimated from age curve: age {age} indicates {age_label}.")
            return age_curve_score, evidence, True

        if production_score is not None:
            blended = round((production_score * 0.45) + (_fallback_midpoint() * 0.55), 3)
            evidence.append("Future-specific age inputs unavailable; using conservative blend of production and neutral dynasty future placeholder.")
            return blended, evidence, True
        evidence.append("Age/future projection unavailable; using neutral placeholder.")
        return _fallback_midpoint(), evidence, False

    if dimension == "contract":
        score = _safe_float(profile.get("contract_score"))
        years_remaining = profile.get("contract_years_remaining")
        status = _safe_str(profile.get("contract_status"))
        if score is not None:
            detail = "Contract score available from normalized contract years"
            if years_remaining is not None:
                detail += f": {years_remaining} years remaining"
            if status:
                detail += f" ({status})"
            evidence.append(detail + ".")
            return score, evidence, True
        evidence.append("Contract data unavailable; using neutral placeholder.")
        return _fallback_midpoint(), evidence, False

    if dimension == "scarcity":
        score = _safe_float(profile.get("scarcity_score"))
        if score is not None:
            evidence.append("Scarcity score available from lineup slots and position pool.")
            return score, evidence, True
        evidence.append("Position scarcity unavailable; using neutral placeholder.")
        return _fallback_midpoint(), evidence, False

    if dimension == "replacement":
        scarcity = _safe_float(profile.get("scarcity_score"), _fallback_midpoint()) or _fallback_midpoint()
        current = _safe_float(profile.get("current_production_score"), _fallback_midpoint()) or _fallback_midpoint()
        score = round((scarcity * 0.45) + (current * 0.55), 3)
        evidence.append("Replacement score estimated from scarcity and current production.")
        return score, evidence, profile.get("current_production_score") is not None

    if dimension == "risk":
        availability = _safe_str(profile.get("availability_status")).lower()
        games_played = _safe_int(profile.get("games_played"))
        age = _safe_float(profile.get("age") or profile.get("age_as_of_season_start"))
        if availability == "unavailable_or_limited":
            evidence.append("Availability status indicates elevated risk.")
            return 35.0, evidence, True

        base_score = None
        if games_played is not None:
            if games_played >= 60:
                base_score = 68.0
                evidence.append("Games played indicates strong current availability.")
            elif games_played >= 35:
                base_score = 56.0
                evidence.append("Games played indicates moderate current availability.")
            else:
                base_score = 42.0
                evidence.append("Low games played indicates elevated availability or role risk.")
        elif availability and availability != "unknown":
            base_score = 65.0
            evidence.append("Availability status available and not flagged as unavailable.")

        if base_score is not None and age is not None:
            if age >= 35:
                base_score -= 10.0
                evidence.append(f"Age {age} adds late-career dynasty risk.")
            elif age >= 32:
                base_score -= 5.0
                evidence.append(f"Age {age} adds moderate age-curve risk.")
            elif age <= 21:
                base_score -= 2.0
                evidence.append(f"Age {age} adds minor development uncertainty.")
            return max(0.0, round(base_score, 3)), evidence, True

        if base_score is not None:
            return base_score, evidence, True

        if age is not None:
            if age >= 35:
                evidence.append(f"Age {age} indicates elevated dynasty risk without injury data.")
                return 42.0, evidence, True
            if age >= 32:
                evidence.append(f"Age {age} indicates moderate dynasty age risk without injury data.")
                return 50.0, evidence, True
            evidence.append(f"Age {age} does not independently flag elevated dynasty risk.")
            return 60.0, evidence, True

        evidence.append("Injury/availability and age data unavailable; using neutral placeholder.")
        return _fallback_midpoint(), evidence, False

    if dimension == "market":
        current = _safe_float(profile.get("current_production_score"), _fallback_midpoint()) or _fallback_midpoint()
        future = _safe_float(profile.get("future_score"), _fallback_midpoint()) or _fallback_midpoint()
        score = round((current * 0.50) + (future * 0.50), 3)
        evidence.append("Market score estimated from current/future blend until transaction history is normalized.")
        return score, evidence, profile.get("future_score") is not None or profile.get("current_production_score") is not None

    if dimension == "fit":
        evidence.append("Strategic fit requires team identity and objective; using neutral placeholder.")
        return _fallback_midpoint(), evidence, False

    if dimension == "chemistry":
        evidence.append("Chemistry requires relationship graph; using neutral placeholder.")
        return _fallback_midpoint(), evidence, False

    return _fallback_midpoint(), ["Unknown dimension; using neutral placeholder."], False


def evaluate_player(profile: dict[str, Any], analysis_profile: dict[str, Any]) -> dict[str, Any]:
    weights = _weights(analysis_profile)
    dimensions: dict[str, float] = {}
    evidence: list[str] = []
    observed_count = 0
    weighted_total = 0.0
    weight_total = 0.0

    for dimension in VALUATION_DIMENSIONS:
        value, dimension_evidence, observed = _dimension_value(profile, dimension)
        weight = weights.get(dimension, 0.5)
        dimensions[dimension] = round(value, 3)
        evidence.extend([f"{dimension}: {item}" for item in dimension_evidence])
        weighted_total += value * weight
        weight_total += weight
        if observed:
            observed_count += 1

    overall = round(weighted_total / weight_total, 3) if weight_total else 0.0

    profile_completeness = _safe_float(profile.get("evidence_completeness"), 0.0) or 0.0
    production_completeness = _safe_float(profile.get("production_evidence_completeness"), 0.0) or 0.0
    bio_completeness = _safe_float(profile.get("bio_evidence_completeness"), 0.0) or 0.0
    contract_completeness = _safe_float(profile.get("contract_evidence_completeness"), 0.0) or 0.0
    base_completeness = max(
        profile_completeness,
        (profile_completeness * 0.45)
        + (production_completeness * 0.27)
        + (bio_completeness * 0.15)
        + (contract_completeness * 0.13),
    )
    dimension_completeness = observed_count / len(VALUATION_DIMENSIONS)
    confidence = round((base_completeness * 0.55) + (dimension_completeness * 0.45), 3)

    return {
        "asset_id": _safe_str(profile.get("asset_id") or profile.get("player_id")),
        "player_id": _safe_str(profile.get("player_id") or profile.get("asset_id")),
        "player_name": _safe_str(profile.get("player_name") or profile.get("name")),
        "position": _safe_str(profile.get("position")),
        "fantasy_team": _safe_str(profile.get("fantasy_team")),
        "nhl_team": _safe_str(profile.get("nhl_team")),
        "nhl_player_id": _safe_str(profile.get("nhl_player_id")),
        "model_key": _safe_str(analysis_profile.get("model_key")),
        "overall_asset_value": overall,
        "dimensions": dimensions,
        "current_points": profile.get("current_points"),
        "current_goals": profile.get("current_goals"),
        "current_assists": profile.get("current_assists"),
        "games_played": profile.get("games_played"),
        "points_per_game": profile.get("points_per_game"),
        "production_rank": profile.get("production_rank"),
        "age": profile.get("age") or profile.get("age_as_of_season_start"),
        "birth_date": profile.get("birth_date"),
        "contract_years_remaining": profile.get("contract_years_remaining"),
        "contract_status": profile.get("contract_status"),
        "keeper_eligible": profile.get("keeper_eligible"),
        "confidence": confidence,
        "evidence": evidence,
    }


def _flatten_for_csv(value: dict[str, Any]) -> dict[str, Any]:
    row = {
        "asset_id": value.get("asset_id"),
        "player_id": value.get("player_id"),
        "player_name": value.get("player_name"),
        "position": value.get("position"),
        "fantasy_team": value.get("fantasy_team"),
        "nhl_team": value.get("nhl_team"),
        "nhl_player_id": value.get("nhl_player_id"),
        "model_key": value.get("model_key"),
        "overall_asset_value": value.get("overall_asset_value"),
        "current_points": value.get("current_points"),
        "current_goals": value.get("current_goals"),
        "current_assists": value.get("current_assists"),
        "games_played": value.get("games_played"),
        "points_per_game": value.get("points_per_game"),
        "production_rank": value.get("production_rank"),
        "age": value.get("age"),
        "birth_date": value.get("birth_date"),
        "contract_years_remaining": value.get("contract_years_remaining"),
        "contract_status": value.get("contract_status"),
        "keeper_eligible": value.get("keeper_eligible"),
        "confidence": value.get("confidence"),
    }
    dimensions = value.get("dimensions", {})
    if isinstance(dimensions, dict):
        for dimension in VALUATION_DIMENSIONS:
            row[f"value_{dimension}"] = dimensions.get(dimension)
    return row


def write_values_csv(path: Path, values: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "asset_id",
        "player_id",
        "player_name",
        "position",
        "fantasy_team",
        "nhl_team",
        "nhl_player_id",
        "model_key",
        "overall_asset_value",
        "current_points",
        "current_goals",
        "current_assists",
        "games_played",
        "points_per_game",
        "production_rank",
        "age",
        "birth_date",
        "contract_years_remaining",
        "contract_status",
        "keeper_eligible",
        "confidence",
        *[f"value_{dimension}" for dimension in VALUATION_DIMENSIONS],
    ]

    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for value in values:
            writer.writerow(_flatten_for_csv(value))


def build_player_values() -> list[dict[str, Any]]:
    log_header("Canonical Valuation Engine")

    players, source = _load_players()
    players, production_matches = _merge_production(players)
    players, bio_matches = _merge_bio(players)
    players, contract_matches = _merge_contracts(players)
    analysis_profile = read_json(ANALYSIS_PROFILE_PATH)
    league_profile = read_json(LEAGUE_PROFILE_PATH)

    values = [evaluate_player(player, analysis_profile) for player in players]
    values.sort(key=lambda item: item.get("overall_asset_value", 0), reverse=True)

    write_json(OUTPUT_JSON, values)
    write_values_csv(OUTPUT_CSV, values)

    avg_value = round(mean([item["overall_asset_value"] for item in values]), 3) if values else 0
    avg_confidence = round(mean([item["confidence"] for item in values]), 3) if values else 0

    log(f"League: {league_profile.get('league_name', '')} ({league_profile.get('season', '')})")
    log(f"Sport: {league_profile.get('sport', '')}")
    log(f"Model Key: {analysis_profile.get('model_key', '')}")
    log(f"Archetype: {analysis_profile.get('archetype_name', '')}")
    log(f"Input Source: {source}")
    log(f"Production Matches: {production_matches}")
    log(f"Bio Matches: {bio_matches}")
    log(f"Contract Matches: {contract_matches}")
    log(f"Players Valued: {len(values)}")
    log(f"Average Value: {avg_value}")
    log(f"Average Confidence: {avg_confidence}")

    log_section("Top Asset Values")
    for item in values[:10]:
        points_text = ""
        if item.get("current_points") is not None:
            points_text = f" | {item.get('current_points')} pts"
        age_text = ""
        if item.get("age") is not None:
            age_text = f" | age {item.get('age')}"
        contract_text = ""
        if item.get("contract_years_remaining") is not None:
            contract_text = f" | contract {item.get('contract_years_remaining')}y"
        log(
            f"  {item.get('player_name')} ({item.get('position')}, {item.get('fantasy_team')}): "
            f"{item.get('overall_asset_value')} | confidence {item.get('confidence')}{points_text}{age_text}{contract_text}"
        )

    log_section("Remaining Limitations")
    log("  Values now consume NHL production, bio/age, and contract data when available.")
    log("  Injuries, transaction history, relationship/chemistry, and manager-market inputs remain future enrichments.")

    log_section("Output Files")
    log(f"JSON: {OUTPUT_JSON}")
    log(f"CSV: {OUTPUT_CSV}")
    log("Completed successfully.")

    return values


if __name__ == "__main__":
    build_player_values()
