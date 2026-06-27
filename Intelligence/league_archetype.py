# -*- coding: utf-8 -*-
"""
League archetype intelligence builder.

Intelligence-layer responsibility:
- Read provider-independent Output/league_profile.json.
- Select the analytical model the engine should use.
- Produce deterministic model-selection guidance for downstream Intelligence and AI modules.

Inputs:
- Output/league_profile.json

Outputs:
- Output/league_archetype.json
- Output/league_archetype.csv
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


GENERATOR_NAME = "Intelligence.league_archetype"
GENERATOR_VERSION = "2.1.0"

INPUT_PROFILE = OUTPUT_DIR / "league_profile.json"
OUTPUT_JSON = OUTPUT_DIR / "league_archetype.json"
OUTPUT_CSV = OUTPUT_DIR / "league_archetype.csv"


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


def load_league_profile() -> Dict[str, Any]:
    profile = read_json(INPUT_PROFILE)

    if not isinstance(profile, dict):
        raise TypeError("Output/league_profile.json must contain a JSON object.")

    return profile


def select_model_key(profile: Dict[str, Any]) -> str:
    roster_continuity = safe_str(profile.get("roster_continuity"), "unknown")
    league_subtype = safe_str(profile.get("league_subtype"), "unknown")
    competition_model = safe_str(profile.get("competition_model"), "unknown")
    scoring_model = safe_str(profile.get("scoring_model"), "unknown")
    scoring_detail = safe_str(profile.get("scoring_detail"), "unknown")

    parts = []

    if league_subtype not in {"", "unknown"}:
        parts.append(league_subtype)
    elif roster_continuity not in {"", "unknown"}:
        parts.append(roster_continuity)
    else:
        parts.append("unknown_continuity")

    if competition_model not in {"", "unknown"}:
        parts.append(competition_model)

    if scoring_detail not in {"", "unknown"}:
        parts.append(scoring_detail)
    elif scoring_model not in {"", "unknown"}:
        parts.append(scoring_model)

    return "_".join(parts)


def select_archetype_name(profile: Dict[str, Any]) -> str:
    roster_continuity = safe_str(profile.get("roster_continuity"), "unknown")
    league_subtype = safe_str(profile.get("league_subtype"), "unknown")
    competition_model = safe_str(profile.get("competition_model"), "unknown")
    scoring_detail = safe_str(profile.get("scoring_detail"), "unknown")

    if league_subtype == "contract_dynasty":
        base = "Contract Dynasty"
    elif roster_continuity == "dynasty":
        base = "Dynasty"
    elif roster_continuity == "keeper":
        base = "Keeper"
    elif roster_continuity == "redraft":
        base = "Redraft"
    elif roster_continuity == "best_ball":
        base = "Best Ball"
    elif roster_continuity == "dfs":
        base = "DFS"
    else:
        base = "Unknown Fantasy Format"

    modifiers = []
    if competition_model == "h2h":
        modifiers.append("Head-to-Head")
    elif competition_model == "total_points":
        modifiers.append("Total Points")
    elif competition_model == "rotisserie":
        modifiers.append("Rotisserie")

    if scoring_detail == "points_only":
        modifiers.append("Points-Only")
    elif scoring_detail == "multi_category":
        modifiers.append("Multi-Category")

    if modifiers:
        return f"{base} ({', '.join(modifiers)})"

    return base


def build_model_priorities(profile: Dict[str, Any]) -> Dict[str, Any]:
    roster_continuity = safe_str(profile.get("roster_continuity"), "unknown")
    league_subtype = safe_str(profile.get("league_subtype"), "unknown")
    competition_model = safe_str(profile.get("competition_model"), "unknown")
    scoring_detail = safe_str(profile.get("scoring_detail"), "unknown")

    priorities = {
        "current_production": "medium",
        "future_value": "medium",
        "age_curve": "medium",
        "contract_value": "conditional",
        "draft_pick_value": "conditional",
        "prospect_value": "conditional",
        "positional_scarcity": "medium",
        "category_scarcity": "conditional",
        "weekly_matchups": "conditional",
        "replacement_value": "medium",
        "risk_tolerance": "balanced",
    }

    if roster_continuity == "redraft":
        priorities.update(
            {
                "current_production": "very_high",
                "future_value": "low",
                "age_curve": "low",
                "contract_value": "none",
                "draft_pick_value": "none",
                "prospect_value": "low",
                "risk_tolerance": "current_season_optimized",
            }
        )

    if roster_continuity == "keeper":
        priorities.update(
            {
                "current_production": "high",
                "future_value": "medium_high",
                "age_curve": "medium_high",
                "draft_pick_value": "medium",
                "prospect_value": "medium",
                "risk_tolerance": "balanced_with_retention_value",
            }
        )

    if roster_continuity == "dynasty":
        priorities.update(
            {
                "current_production": "high",
                "future_value": "very_high",
                "age_curve": "very_high",
                "draft_pick_value": "very_high",
                "prospect_value": "very_high",
                "replacement_value": "high",
                "risk_tolerance": "window_based",
            }
        )

    if league_subtype == "contract_dynasty":
        priorities.update(
            {
                "contract_value": "very_high",
                "contract_expiry_risk": "very_high",
                "asset_lifecycle": "very_high",
                "replacement_cycle": "high",
            }
        )

    if competition_model == "h2h":
        priorities["weekly_matchups"] = "high"
        priorities["playoff_schedule"] = "high"

    if scoring_detail == "points_only":
        priorities["category_scarcity"] = "none"
        priorities["primary_stat_basis"] = "goals_assists_points"

    if scoring_detail == "multi_category":
        priorities["category_scarcity"] = "very_high"
        priorities["category_balance"] = "very_high"

    return priorities


def build_supported_decisions(profile: Dict[str, Any]) -> List[str]:
    roster_continuity = safe_str(profile.get("roster_continuity"), "unknown")
    league_subtype = safe_str(profile.get("league_subtype"), "unknown")
    competition_model = safe_str(profile.get("competition_model"), "unknown")

    decisions = [
        "player_value",
        "positional_depth",
        "waiver_priority",
        "lineup_recommendation",
    ]

    if competition_model == "h2h":
        decisions.extend(["weekly_matchup", "playoff_timing"])

    if roster_continuity in {"keeper", "dynasty"}:
        decisions.extend(["trade_value", "keeper_value", "draft_pick_value", "future_window"])

    if roster_continuity == "dynasty":
        decisions.extend(["prospect_value", "team_direction", "competitive_window", "asset_lifecycle"])

    if league_subtype == "contract_dynasty":
        decisions.extend(["contract_expiry_risk", "contract_surplus_value", "replacement_planning"])

    return sorted(set(decisions))


def calculate_confidence(profile: Dict[str, Any]) -> float:
    confidence = profile.get("confidence", {}) or {}

    if not isinstance(confidence, dict):
        return 0.0

    keys = [
        "scoring_model",
        "scoring_detail",
        "competition_model",
        "roster_continuity",
        "league_subtype",
        "lineup_model",
        "planning_horizon",
    ]

    values = [safe_float(confidence.get(key)) for key in keys if key in confidence]

    if not values:
        return 0.0

    return round(sum(values) / len(values), 3)


def build_archetype() -> Dict[str, Any]:
    profile = load_league_profile()

    archetype = {
        "league_id": profile.get("league_id", ""),
        "league_name": profile.get("league_name", ""),
        "season": profile.get("season", ""),
        "sport": profile.get("sport", ""),
        "archetype_name": select_archetype_name(profile),
        "model_key": select_model_key(profile),
        "roster_continuity": profile.get("roster_continuity", "unknown"),
        "league_subtype": profile.get("league_subtype", "unknown"),
        "competition_model": profile.get("competition_model", "unknown"),
        "scoring_model": profile.get("scoring_model", "unknown"),
        "scoring_detail": profile.get("scoring_detail", "unknown"),
        "lineup_model": profile.get("lineup_model", "unknown"),
        "planning_horizon": profile.get("planning_horizon", "unknown"),
        "asset_classes": profile.get("asset_classes", []),
        "model_priorities": build_model_priorities(profile),
        "supported_decisions": build_supported_decisions(profile),
        "confidence": calculate_confidence(profile),
        "evidence": profile.get("inference_evidence", {}),
        "source": {
            "input_file": str(INPUT_PROFILE),
            "generator": GENERATOR_NAME,
            "generator_version": GENERATOR_VERSION,
        },
    }

    return archetype


def write_csv(archetype: Dict[str, Any]) -> None:
    ensure_project_dirs()

    fieldnames = ["field", "value"]
    rows = [
        {"field": "league_name", "value": archetype.get("league_name", "")},
        {"field": "season", "value": archetype.get("season", "")},
        {"field": "sport", "value": archetype.get("sport", "")},
        {"field": "archetype_name", "value": archetype.get("archetype_name", "")},
        {"field": "model_key", "value": archetype.get("model_key", "")},
        {"field": "roster_continuity", "value": archetype.get("roster_continuity", "")},
        {"field": "league_subtype", "value": archetype.get("league_subtype", "")},
        {"field": "competition_model", "value": archetype.get("competition_model", "")},
        {"field": "scoring_detail", "value": archetype.get("scoring_detail", "")},
        {"field": "planning_horizon", "value": archetype.get("planning_horizon", "")},
        {"field": "confidence", "value": archetype.get("confidence", 0)},
        {"field": "supported_decisions", "value": ",".join(archetype.get("supported_decisions", []))},
    ]

    for key, value in archetype.get("model_priorities", {}).items():
        rows.append({"field": f"priority_{key}", "value": value})

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(archetype: Dict[str, Any]) -> None:
    ensure_project_dirs()
    write_json(OUTPUT_JSON, archetype)
    write_csv(archetype)


def print_summary(archetype: Dict[str, Any]) -> None:
    log_header("League Archetype Intelligence Builder")
    log(f"League: {archetype.get('league_name')} ({archetype.get('season')})")
    log(f"Sport: {archetype.get('sport')}")
    log(f"Archetype: {archetype.get('archetype_name')}")
    log(f"Model Key: {archetype.get('model_key')}")
    log(f"Planning Horizon: {archetype.get('planning_horizon')}")
    log(f"Confidence: {archetype.get('confidence')}")

    log_section("Supported Decisions")
    for decision in archetype.get("supported_decisions", []):
        log(f"  - {decision}")

    log("")
    log_section("Output Files")
    log(f"JSON: {OUTPUT_JSON}")
    log(f"CSV: {OUTPUT_CSV}")
    log("Completed successfully.")


def main() -> None:
    archetype = build_archetype()
    write_outputs(archetype)
    print_summary(archetype)


if __name__ == "__main__":
    main()
