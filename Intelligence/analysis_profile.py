# -*- coding: utf-8 -*-
"""
Analysis profile builder.

Intelligence-layer responsibility:
- Read provider-independent league profile and league archetype outputs.
- Convert the selected archetype/model into deterministic valuation weights.
- Produce the analysis profile consumed by the canonical valuation engine.

Inputs:
- Output/league_profile.json
- Output/league_archetype.json

Outputs:
- Output/analysis_profile.json
- Output/analysis_profile.csv
"""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import csv
from typing import Any, Dict, List

from Core.json_utils import read_json, write_json
from Core.logger import log, log_header, log_section
from Core.project_paths import OUTPUT_DIR, ensure_project_dirs


GENERATOR_NAME = "Intelligence.analysis_profile"
GENERATOR_VERSION = "1.0.0"

INPUT_LEAGUE_PROFILE = OUTPUT_DIR / "league_profile.json"
INPUT_LEAGUE_ARCHETYPE = OUTPUT_DIR / "league_archetype.json"

OUTPUT_JSON = OUTPUT_DIR / "analysis_profile.json"
OUTPUT_CSV = OUTPUT_DIR / "analysis_profile.csv"


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


def safe_str(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    return str(value)


def safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return fallback
        return float(value)
    except (TypeError, ValueError):
        return fallback


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def rounded_weights(weights: Dict[str, float]) -> Dict[str, float]:
    return {key: round(clamp(value), 3) for key, value in weights.items()}


def load_inputs() -> tuple[Dict[str, Any], Dict[str, Any]]:
    league_profile = read_json(INPUT_LEAGUE_PROFILE)
    league_archetype = read_json(INPUT_LEAGUE_ARCHETYPE)

    if not isinstance(league_profile, dict):
        raise TypeError("Output/league_profile.json must contain a JSON object.")

    if not isinstance(league_archetype, dict):
        raise TypeError("Output/league_archetype.json must contain a JSON object.")

    return league_profile, league_archetype


def build_base_weights() -> Dict[str, float]:
    return {
        "current": 0.60,
        "future": 0.50,
        "contract": 0.25,
        "scarcity": 0.50,
        "replacement": 0.50,
        "risk": 0.45,
        "market": 0.45,
        "fit": 0.45,
        "chemistry": 0.20,
    }


def apply_roster_continuity(weights: Dict[str, float], roster_continuity: str) -> None:
    if roster_continuity == "redraft":
        weights.update(
            {
                "current": 0.90,
                "future": 0.15,
                "contract": 0.00,
                "scarcity": 0.60,
                "replacement": 0.75,
                "risk": 0.60,
                "market": 0.45,
                "fit": 0.55,
                "chemistry": 0.35,
            }
        )

    elif roster_continuity == "keeper":
        weights.update(
            {
                "current": 0.75,
                "future": 0.65,
                "contract": 0.35,
                "scarcity": 0.60,
                "replacement": 0.60,
                "risk": 0.55,
                "market": 0.55,
                "fit": 0.60,
                "chemistry": 0.30,
            }
        )

    elif roster_continuity == "dynasty":
        weights.update(
            {
                "current": 0.72,
                "future": 0.90,
                "contract": 0.65,
                "scarcity": 0.70,
                "replacement": 0.60,
                "risk": 0.55,
                "market": 0.65,
                "fit": 0.75,
                "chemistry": 0.35,
            }
        )

    elif roster_continuity == "best_ball":
        weights.update(
            {
                "current": 0.78,
                "future": 0.30,
                "contract": 0.00,
                "scarcity": 0.55,
                "replacement": 0.25,
                "risk": 0.50,
                "market": 0.45,
                "fit": 0.45,
                "chemistry": 0.30,
            }
        )

    elif roster_continuity == "dfs":
        weights.update(
            {
                "current": 0.95,
                "future": 0.00,
                "contract": 0.00,
                "scarcity": 0.45,
                "replacement": 0.70,
                "risk": 0.70,
                "market": 0.65,
                "fit": 0.65,
                "chemistry": 0.45,
            }
        )


def apply_league_subtype(weights: Dict[str, float], league_subtype: str) -> None:
    if league_subtype == "contract_dynasty":
        weights["contract"] = max(weights["contract"], 0.82)
        weights["future"] = max(weights["future"], 0.90)
        weights["market"] = max(weights["market"], 0.68)
        weights["fit"] = max(weights["fit"], 0.78)
        weights["risk"] = max(weights["risk"], 0.58)


def apply_competition_model(weights: Dict[str, float], competition_model: str) -> None:
    if competition_model == "total_points":
        weights["current"] = max(weights["current"], 0.74)
        weights["replacement"] = max(weights["replacement"], 0.62)
        weights["risk"] = max(weights["risk"], 0.58)

    elif competition_model == "h2h":
        weights["current"] = max(weights["current"], 0.72)
        weights["fit"] = max(weights["fit"], 0.68)
        weights["chemistry"] = max(weights["chemistry"], 0.42)

    elif competition_model == "rotisserie":
        weights["scarcity"] = max(weights["scarcity"], 0.78)
        weights["replacement"] = max(weights["replacement"], 0.65)


def apply_scoring_detail(weights: Dict[str, float], scoring_detail: str) -> None:
    if scoring_detail == "points_only":
        weights["current"] = max(weights["current"], 0.76)
        weights["scarcity"] = min(max(weights["scarcity"], 0.58), 0.72)

    elif scoring_detail == "multi_category":
        weights["scarcity"] = max(weights["scarcity"], 0.82)
        weights["replacement"] = max(weights["replacement"], 0.70)
        weights["fit"] = max(weights["fit"], 0.72)


def build_weights(league_profile: Dict[str, Any], league_archetype: Dict[str, Any]) -> Dict[str, float]:
    weights = build_base_weights()

    roster_continuity = safe_str(league_profile.get("roster_continuity"), "unknown")
    league_subtype = safe_str(league_profile.get("league_subtype"), "unknown")
    competition_model = safe_str(league_profile.get("competition_model"), "unknown")
    scoring_detail = safe_str(league_profile.get("scoring_detail"), "unknown")

    apply_roster_continuity(weights, roster_continuity)
    apply_league_subtype(weights, league_subtype)
    apply_competition_model(weights, competition_model)
    apply_scoring_detail(weights, scoring_detail)

    # Archetype confidence can soften aggressive model assumptions if upstream confidence is low.
    confidence = safe_float(league_archetype.get("confidence"), 0.0)
    if 0.0 < confidence < 0.75:
        base = build_base_weights()
        for key in weights:
            weights[key] = (weights[key] * confidence) + (base[key] * (1 - confidence))

    return rounded_weights(weights)


def build_dimension_roles() -> Dict[str, str]:
    return {
        "current": "Intrinsic value dimension for current production and near-term contribution.",
        "future": "Intrinsic value dimension for multi-year contribution and asset runway.",
        "contract": "Intrinsic/contextual dimension for contract term, expiry, surplus, and replacement pressure.",
        "scarcity": "League-context dimension for position and asset scarcity.",
        "replacement": "League-context dimension for how difficult the asset is to replace.",
        "risk": "Penalty dimension for uncertainty, volatility, injury, age, and role risk.",
        "market": "Market-context dimension for likely demand, hype, liquidity, and perceived price.",
        "fit": "Strategic-context dimension for team-specific usefulness and objective alignment.",
        "chemistry": "Relationship-context dimension for coach, linemate, deployment, system, and usage effects.",
    }


def build_data_readiness() -> Dict[str, str]:
    return {
        "current": "available_initially_from_player_master_if_points_or_rank_fields_exist",
        "future": "partial_until_age_projection_and_prospect_inputs_are_available",
        "contract": "partial_until_contract_years_are_normalized",
        "scarcity": "partial_from_league_roster_slots_and_position_counts",
        "replacement": "partial_until_free_agent_or_waiver_pool_is_available",
        "risk": "partial_until_injury_age_and_volatility_inputs_are_available",
        "market": "limited_until_transaction_history_and_owner_behavior_are_available",
        "fit": "limited_until_team_profiles_and_team_direction_are_available",
        "chemistry": "reserved_until_relationship_graph_coach_linemate_and_deployment_inputs_are_available",
    }


def build_evidence(league_profile: Dict[str, Any], league_archetype: Dict[str, Any], weights: Dict[str, float]) -> List[str]:
    evidence = []

    model_key = safe_str(league_archetype.get("model_key"), "unknown")
    archetype_name = safe_str(league_archetype.get("archetype_name"), "Unknown")
    competition_model = safe_str(league_profile.get("competition_model"), "unknown")
    scoring_detail = safe_str(league_profile.get("scoring_detail"), "unknown")
    league_subtype = safe_str(league_profile.get("league_subtype"), "unknown")

    evidence.append(f"Selected model key: {model_key}")
    evidence.append(f"League archetype: {archetype_name}")

    if league_subtype == "contract_dynasty":
        evidence.append("Contract dynasty model increases future, contract, market, and strategic-fit weighting.")

    if competition_model == "total_points":
        evidence.append("Total-points competition emphasizes cumulative production and roster efficiency over weekly matchup timing.")

    if scoring_detail == "points_only":
        evidence.append("Points-only scoring keeps category scarcity inactive and prioritizes goals/assists production basis.")

    if weights.get("chemistry", 0) > 0:
        evidence.append("Chemistry is included as a reserved relationship dimension but remains low-confidence until relationship inputs exist.")

    return evidence


def build_recommended_next_inputs(league_profile: Dict[str, Any]) -> List[str]:
    next_inputs = [
        "normalized_contract_years",
        "age_or_birthdate",
        "current_season_points_or_projection",
        "position_level_replacement_pool",
        "team_roster_assignments",
    ]

    if safe_str(league_profile.get("league_subtype")) == "contract_dynasty":
        next_inputs.extend(["contract_expiry_year", "keeper_eligibility", "draft_pick_inventory"])

    next_inputs.extend(["transaction_history", "injury_status", "relationship_graph"])

    return sorted(set(next_inputs))


def build_analysis_profile() -> Dict[str, Any]:
    league_profile, league_archetype = load_inputs()
    weights = build_weights(league_profile, league_archetype)

    analysis_profile = {
        "league_id": league_profile.get("league_id", ""),
        "league_name": league_profile.get("league_name", ""),
        "season": league_profile.get("season", ""),
        "sport": league_profile.get("sport", ""),
        "model_key": league_archetype.get("model_key", "unknown"),
        "archetype_name": league_archetype.get("archetype_name", "Unknown"),
        "planning_horizon": league_profile.get("planning_horizon", "unknown"),
        "roster_continuity": league_profile.get("roster_continuity", "unknown"),
        "league_subtype": league_profile.get("league_subtype", "unknown"),
        "competition_model": league_profile.get("competition_model", "unknown"),
        "scoring_model": league_profile.get("scoring_model", "unknown"),
        "scoring_detail": league_profile.get("scoring_detail", "unknown"),
        "valuation_dimensions": VALUATION_DIMENSIONS,
        "weights": weights,
        "dimension_roles": build_dimension_roles(),
        "data_readiness": build_data_readiness(),
        "supported_value_layers": [
            "intrinsic",
            "situational",
            "market",
            "strategic",
        ],
        "reserved_future_dimensions": [
            "coach_system_fit",
            "linemate_chemistry",
            "power_play_deployment",
            "salary_cap_context",
            "owner_market_behavior",
            "event_impact_delta",
        ],
        "recommended_next_inputs": build_recommended_next_inputs(league_profile),
        "confidence": {
            "profile_confidence": league_profile.get("confidence", {}),
            "archetype_confidence": league_archetype.get("confidence", 0),
            "analysis_profile_confidence": round(
                safe_float(league_archetype.get("confidence"), 0.0) * 0.95,
                3,
            ),
        },
        "evidence": build_evidence(league_profile, league_archetype, weights),
        "source": {
            "input_files": [str(INPUT_LEAGUE_PROFILE), str(INPUT_LEAGUE_ARCHETYPE)],
            "generator": GENERATOR_NAME,
            "generator_version": GENERATOR_VERSION,
        },
    }

    return analysis_profile


def write_csv(profile: Dict[str, Any]) -> None:
    ensure_project_dirs()

    rows = [
        {"section": "identity", "field": "league_name", "value": profile.get("league_name", "")},
        {"section": "identity", "field": "season", "value": profile.get("season", "")},
        {"section": "identity", "field": "sport", "value": profile.get("sport", "")},
        {"section": "identity", "field": "model_key", "value": profile.get("model_key", "")},
        {"section": "identity", "field": "archetype_name", "value": profile.get("archetype_name", "")},
        {"section": "identity", "field": "planning_horizon", "value": profile.get("planning_horizon", "")},
        {"section": "identity", "field": "competition_model", "value": profile.get("competition_model", "")},
        {"section": "identity", "field": "scoring_detail", "value": profile.get("scoring_detail", "")},
    ]

    for key, value in profile.get("weights", {}).items():
        rows.append({"section": "weights", "field": key, "value": value})

    for key, value in profile.get("data_readiness", {}).items():
        rows.append({"section": "data_readiness", "field": key, "value": value})

    for item in profile.get("recommended_next_inputs", []):
        rows.append({"section": "recommended_next_inputs", "field": item, "value": "needed"})

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=["section", "field", "value"])
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(profile: Dict[str, Any]) -> None:
    ensure_project_dirs()
    write_json(OUTPUT_JSON, profile)
    write_csv(profile)


def print_summary(profile: Dict[str, Any]) -> None:
    log_header("Analysis Profile Builder")
    log(f"League: {profile.get('league_name')} ({profile.get('season')})")
    log(f"Sport: {profile.get('sport')}")
    log(f"Model Key: {profile.get('model_key')}")
    log(f"Archetype: {profile.get('archetype_name')}")
    log(f"Planning Horizon: {profile.get('planning_horizon')}")
    log(f"Analysis Confidence: {profile.get('confidence', {}).get('analysis_profile_confidence')}")

    log_section("Valuation Weights")
    for key in VALUATION_DIMENSIONS:
        log(f"  {key}: {profile.get('weights', {}).get(key)}")

    log_section("Recommended Next Inputs")
    for item in profile.get("recommended_next_inputs", []):
        log(f"  - {item}")

    log("")
    log_section("Output Files")
    log(f"JSON: {OUTPUT_JSON}")
    log(f"CSV: {OUTPUT_CSV}")
    log("Completed successfully.")


def main() -> None:
    profile = build_analysis_profile()
    write_outputs(profile)
    print_summary(profile)


if __name__ == "__main__":
    main()
