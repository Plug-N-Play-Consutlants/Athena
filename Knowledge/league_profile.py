# -*- coding: utf-8 -*-
"""
League profile knowledge builder.

Knowledge-layer responsibility:
- Read provider-neutral Output/league_settings.json.
- Read optional workspace rule confirmations from Configuration/workspace_rules.json.
- Infer the league's operating profile deterministically.
- Produce a provider-independent league profile for Intelligence modules.

Inputs:
- Output/league_settings.json
- Configuration/workspace_rules.json optional

Outputs:
- Output/league_profile.json
- Output/league_profile.csv
"""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import csv
from typing import Any, Dict, List

from Core.json_utils import read_json, read_optional_json, write_json
from Core.logger import log, log_header, log_section
from Core.project_paths import CONFIGURATION_DIR, OUTPUT_DIR, ensure_project_dirs


GENERATOR_NAME = "Knowledge.league_profile"
GENERATOR_VERSION = "2.1.0"

INPUT_SETTINGS = OUTPUT_DIR / "league_settings.json"
INPUT_WORKSPACE_RULES = CONFIGURATION_DIR / "workspace_rules.json"
OUTPUT_JSON = OUTPUT_DIR / "league_profile.json"
OUTPUT_CSV = OUTPUT_DIR / "league_profile.csv"


VALID_ROSTER_CONTINUITY = {"redraft", "keeper", "dynasty", "best_ball", "dfs"}
VALID_COMPETITION_MODELS = {"h2h", "total_points", "rotisserie", "roto"}
VALID_LINEUP_LOCK_MODELS = {"daily", "weekly", "best_ball", "no_lock"}


def safe_str(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    return str(value)


def safe_int(value: Any, fallback: int = 0) -> int:
    try:
        if value in (None, ""):
            return fallback
        return int(value)
    except (TypeError, ValueError):
        return fallback


def normalize_enum(value: Any) -> str:
    return safe_str(value).strip().lower().replace(" ", "_").replace("-", "_")


def load_league_settings() -> Dict[str, Any]:
    settings = read_json(INPUT_SETTINGS)

    if not isinstance(settings, dict):
        raise TypeError("Output/league_settings.json must contain a JSON object.")

    return settings


def load_workspace_rules() -> Dict[str, Any]:
    rules = read_optional_json(INPUT_WORKSPACE_RULES)

    if rules is None:
        return {}

    if not isinstance(rules, dict):
        raise TypeError("Configuration/workspace_rules.json must contain a JSON object when present.")

    return rules


def infer_scoring_model(settings: Dict[str, Any], rules: Dict[str, Any]) -> Dict[str, Any]:
    scoring = settings.get("scoring", {}) or {}
    scoring_type = normalize_enum(scoring.get("type"))
    categories = scoring.get("categories", []) or []

    if rules.get("scoring_model"):
        return {
            "value": normalize_enum(rules.get("scoring_model")),
            "source": "workspace_rules",
            "confidence": 0.98,
            "evidence": ["workspace_rules.scoring_model supplied"],
        }

    if scoring_type == "points":
        return {
            "value": "points",
            "source": "provider_settings",
            "confidence": 0.95,
            "evidence": ["league_settings.scoring.type is points"],
        }

    if scoring_type in {"roto", "rotisserie"}:
        return {
            "value": "rotisserie",
            "source": "provider_settings",
            "confidence": 0.9,
            "evidence": [f"league_settings.scoring.type is {scoring_type}"],
        }

    if len(categories) > 1:
        return {
            "value": "categories",
            "source": "inferred",
            "confidence": 0.75,
            "evidence": [f"{len(categories)} scoring categories detected"],
        }

    if len(categories) == 1:
        return {
            "value": "points",
            "source": "inferred",
            "confidence": 0.7,
            "evidence": ["single scoring category detected"],
        }

    return {
        "value": "unknown",
        "source": "unresolved",
        "confidence": 0.0,
        "evidence": [],
    }


def infer_scoring_detail(settings: Dict[str, Any], rules: Dict[str, Any]) -> Dict[str, Any]:
    if rules.get("scoring_detail"):
        return {
            "value": normalize_enum(rules.get("scoring_detail")),
            "source": "workspace_rules",
            "confidence": 0.98,
            "evidence": ["workspace_rules.scoring_detail supplied"],
        }

    categories = settings.get("scoring", {}).get("categories", []) or []

    if len(categories) == 1:
        category = categories[0]
        name = safe_str(category.get("category_name") or category.get("category_short_name")).lower()
        if "point" in name:
            return {
                "value": "points_only",
                "source": "provider_settings",
                "confidence": 0.95,
                "evidence": ["single scoring category is points"],
            }

    if len(categories) > 1:
        return {
            "value": "multi_category",
            "source": "provider_settings",
            "confidence": 0.85,
            "evidence": [f"{len(categories)} scoring categories detected"],
        }

    return {
        "value": "unknown",
        "source": "unresolved",
        "confidence": 0.0,
        "evidence": [],
    }


def infer_competition_model(settings: Dict[str, Any], rules: Dict[str, Any]) -> Dict[str, Any]:
    value = normalize_enum(rules.get("competition_model"))

    if value == "roto":
        value = "rotisserie"

    if value in VALID_COMPETITION_MODELS:
        return {
            "value": value,
            "source": "workspace_rules",
            "confidence": 0.98,
            "evidence": ["workspace_rules.competition_model supplied"],
        }

    return {
        "value": "unknown",
        "source": "unresolved",
        "confidence": 0.0,
        "evidence": ["competition model not exposed by current provider settings"],
    }


def infer_roster_continuity(settings: Dict[str, Any], rules: Dict[str, Any]) -> Dict[str, Any]:
    explicit_value = normalize_enum(rules.get("roster_continuity"))

    if explicit_value in VALID_ROSTER_CONTINUITY:
        evidence = ["workspace_rules.roster_continuity supplied"]
        keeper_count = safe_int(rules.get("keeper_count"))
        contract_years = safe_int(rules.get("contract_years"))
        historical_seasons = safe_int(rules.get("historical_seasons"))

        if keeper_count:
            evidence.append(f"keeper_count is {keeper_count}")
        if contract_years:
            evidence.append(f"contract_years is {contract_years}")
        if historical_seasons:
            evidence.append(f"historical_seasons is {historical_seasons}")

        return {
            "value": explicit_value,
            "source": "workspace_rules",
            "confidence": 0.99,
            "evidence": evidence,
        }

    keeper_count = safe_int(rules.get("keeper_count"))
    contract_years = safe_int(rules.get("contract_years"))
    historical_seasons = safe_int(rules.get("historical_seasons"))
    asset_classes = rules.get("asset_classes", []) or []

    dynasty_signals = []
    keeper_signals = []

    if keeper_count >= 8:
        dynasty_signals.append(f"large keeper count detected: {keeper_count}")
    elif keeper_count > 0:
        keeper_signals.append(f"keeper count detected: {keeper_count}")

    if contract_years >= 2:
        dynasty_signals.append(f"multi-year contracts detected: {contract_years}")

    if "draft_picks" in asset_classes:
        dynasty_signals.append("draft pick assets enabled")

    if historical_seasons >= 5:
        dynasty_signals.append(f"long-running league history detected: {historical_seasons} seasons")

    if len(dynasty_signals) >= 2:
        return {
            "value": "dynasty",
            "source": "inferred_from_rules",
            "confidence": 0.9,
            "evidence": dynasty_signals,
        }

    if keeper_signals:
        return {
            "value": "keeper",
            "source": "inferred_from_rules",
            "confidence": 0.75,
            "evidence": keeper_signals,
        }

    return {
        "value": "unknown",
        "source": "unresolved",
        "confidence": 0.0,
        "evidence": ["keeper/contract continuity not exposed by current provider settings"],
    }


def infer_league_subtype(roster_continuity: str, rules: Dict[str, Any]) -> Dict[str, Any]:
    explicit_subtype = normalize_enum(rules.get("league_subtype"))

    if explicit_subtype:
        return {
            "value": explicit_subtype,
            "source": "workspace_rules",
            "confidence": 0.99,
            "evidence": ["workspace_rules.league_subtype supplied"],
        }

    contract_years = safe_int(rules.get("contract_years"))
    contract_model = normalize_enum(rules.get("contract_model"))

    if roster_continuity == "dynasty" and (contract_years >= 2 or "contract" in contract_model):
        return {
            "value": "contract_dynasty",
            "source": "inferred_from_rules",
            "confidence": 0.9,
            "evidence": ["dynasty continuity with multi-year contract rules"],
        }

    if roster_continuity == "dynasty":
        return {
            "value": "standard_dynasty",
            "source": "inferred_from_roster_continuity",
            "confidence": 0.8,
            "evidence": ["dynasty roster continuity detected"],
        }

    if roster_continuity != "unknown":
        return {
            "value": roster_continuity,
            "source": "derived_from_roster_continuity",
            "confidence": 0.8,
            "evidence": [f"roster_continuity is {roster_continuity}"],
        }

    return {
        "value": "unknown",
        "source": "unresolved",
        "confidence": 0.0,
        "evidence": [],
    }


def infer_lineup_model(settings: Dict[str, Any], rules: Dict[str, Any]) -> Dict[str, Any]:
    lock_model = normalize_enum(rules.get("lineup_lock_model"))

    if lock_model in VALID_LINEUP_LOCK_MODELS:
        if lock_model == "best_ball":
            value = "best_ball"
        elif lock_model == "weekly":
            value = "active_lineup_weekly_lock"
        elif lock_model == "daily":
            value = "active_lineup_daily_lock"
        else:
            value = "active_lineup_no_lock"

        return {
            "value": value,
            "lock_model": lock_model,
            "source": "workspace_rules",
            "confidence": 0.98,
            "evidence": ["workspace_rules.lineup_lock_model supplied"],
        }

    return {
        "value": "active_lineup_unknown_lock",
        "lock_model": "unknown",
        "source": "unresolved",
        "confidence": 0.2,
        "evidence": ["active lineup slots detected but lineup lock not exposed by current provider settings"],
    }


def infer_planning_horizon(roster_continuity: str, rules: Dict[str, Any]) -> Dict[str, Any]:
    explicit_value = normalize_enum(rules.get("planning_horizon"))

    if explicit_value:
        return {
            "value": explicit_value,
            "source": "workspace_rules",
            "confidence": 0.98,
            "evidence": ["workspace_rules.planning_horizon supplied"],
        }

    mapping = {
        "redraft": "current_season",
        "keeper": "current_plus_keeper_window",
        "dynasty": "multi_year",
        "best_ball": "current_season",
        "dfs": "single_slate",
    }

    value = mapping.get(roster_continuity, "unknown")
    return {
        "value": value,
        "source": "inferred_from_roster_continuity" if value != "unknown" else "unresolved",
        "confidence": 0.8 if value != "unknown" else 0.0,
        "evidence": [f"roster_continuity is {roster_continuity}"] if value != "unknown" else [],
    }


def infer_asset_classes(roster_continuity: str, rules: Dict[str, Any]) -> Dict[str, Any]:
    explicit_assets = rules.get("asset_classes")

    if isinstance(explicit_assets, list) and explicit_assets:
        return {
            "value": [normalize_enum(asset) for asset in explicit_assets],
            "source": "workspace_rules",
            "confidence": 0.98,
            "evidence": ["workspace_rules.asset_classes supplied"],
        }

    assets = ["players"]

    if roster_continuity in {"keeper", "dynasty", "unknown"}:
        assets.extend(["draft_picks", "contracts"])

    return {
        "value": assets,
        "source": "inferred_from_roster_continuity",
        "confidence": 0.75,
        "evidence": [f"asset classes inferred from roster_continuity={roster_continuity}"],
    }


def infer_model_adjustments(profile: Dict[str, Any]) -> Dict[str, Any]:
    scoring_model = profile.get("scoring_model")
    scoring_detail = profile.get("scoring_detail")
    roster_continuity = profile.get("roster_continuity")
    league_subtype = profile.get("league_subtype")
    competition_model = profile.get("competition_model")

    adjustments = {
        "current_production_weight": "standard",
        "future_value_weight": "unknown_until_roster_continuity_known",
        "positional_scarcity_weight": "enabled",
        "category_scarcity_weight": "conditional",
        "contract_value_weight": "conditional",
        "draft_pick_value_weight": "conditional",
        "weekly_matchup_weight": "conditional",
        "primary_player_value_basis": "unknown",
    }

    if scoring_model == "points" and scoring_detail == "points_only":
        adjustments["category_scarcity_weight"] = "disabled_points_only"
        adjustments["primary_player_value_basis"] = "projected_points"

    if competition_model == "h2h":
        adjustments["weekly_matchup_weight"] = "enabled"

    if roster_continuity == "redraft":
        adjustments["future_value_weight"] = "low"
        adjustments["contract_value_weight"] = "disabled"
        adjustments["draft_pick_value_weight"] = "disabled"

    if roster_continuity == "keeper":
        adjustments["future_value_weight"] = "medium"
        adjustments["contract_value_weight"] = "enabled_if_available"
        adjustments["draft_pick_value_weight"] = "enabled_if_available"

    if roster_continuity == "dynasty":
        adjustments["future_value_weight"] = "high"
        adjustments["draft_pick_value_weight"] = "enabled"
        adjustments["age_curve_weight"] = "high"
        adjustments["prospect_value_weight"] = "high"
        adjustments["competitive_window_weight"] = "high"

    if league_subtype == "contract_dynasty":
        adjustments["contract_value_weight"] = "high"
        adjustments["contract_expiry_risk_weight"] = "high"
        adjustments["replacement_cycle_weight"] = "enabled"

    return adjustments


def build_evidence_map(*inferences: Dict[str, Any]) -> Dict[str, Any]:
    evidence = {}
    for item in inferences:
        key = item.get("key")
        if not key:
            continue
        evidence[key] = {
            "source": item.get("source"),
            "confidence": item.get("confidence"),
            "evidence": item.get("evidence", []),
        }
    return evidence


def build_league_profile() -> Dict[str, Any]:
    settings = load_league_settings()
    rules = load_workspace_rules()

    scoring_model = infer_scoring_model(settings, rules)
    scoring_detail = infer_scoring_detail(settings, rules)
    competition_model = infer_competition_model(settings, rules)
    roster_continuity = infer_roster_continuity(settings, rules)
    league_subtype = infer_league_subtype(roster_continuity["value"], rules)
    lineup_model = infer_lineup_model(settings, rules)
    planning_horizon = infer_planning_horizon(roster_continuity["value"], rules)
    asset_classes = infer_asset_classes(roster_continuity["value"], rules)

    inferences = [
        {"key": "scoring_model", **scoring_model},
        {"key": "scoring_detail", **scoring_detail},
        {"key": "competition_model", **competition_model},
        {"key": "roster_continuity", **roster_continuity},
        {"key": "league_subtype", **league_subtype},
        {"key": "lineup_model", **lineup_model},
        {"key": "planning_horizon", **planning_horizon},
        {"key": "asset_classes", **asset_classes},
    ]

    profile = {
        "league_id": settings.get("league_id", ""),
        "league_name": settings.get("league_name", ""),
        "season": settings.get("season", ""),
        "sport": settings.get("sport", ""),
        "provider": settings.get("provider", ""),
        "team_count": settings.get("team_count", 0),
        "roster_continuity": roster_continuity["value"],
        "league_subtype": league_subtype["value"],
        "lineup_model": lineup_model["value"],
        "lineup_lock_model": lineup_model.get("lock_model", "unknown"),
        "scoring_model": scoring_model["value"],
        "scoring_detail": scoring_detail["value"],
        "competition_model": competition_model["value"],
        "planning_horizon": planning_horizon["value"],
        "asset_classes": asset_classes["value"],
        "keeper_count": safe_int(rules.get("keeper_count")),
        "contract_model": normalize_enum(rules.get("contract_model")) or "unknown",
        "contract_years": safe_int(rules.get("contract_years")),
        "historical_seasons": safe_int(rules.get("historical_seasons")),
        "lineup_slots": settings.get("roster", {}).get("lineup_slots", []),
        "roster_limits": {
            "max_total_players": settings.get("roster", {}).get("max_total_players", 0),
            "max_total_active_players": settings.get("roster", {}).get("max_total_active_players", 0),
            "max_total_reserve_players": settings.get("roster", {}).get("max_total_reserve_players", 0),
        },
        "draft": settings.get("draft", {}),
        "model_adjustments": {},
        "confidence": {
            item["key"]: item.get("confidence", 0.0) for item in inferences
        },
        "inference_evidence": build_evidence_map(*inferences),
        "missing_rule_inputs": [],
        "workspace_rules_loaded": bool(rules),
        "source": {
            "input_file": str(INPUT_SETTINGS),
            "workspace_rules_file": str(INPUT_WORKSPACE_RULES),
            "generator": GENERATOR_NAME,
            "generator_version": GENERATOR_VERSION,
        },
    }

    missing = []
    if competition_model["value"] == "unknown":
        missing.append("competition_model: h2h, total_points, or roto")
    if roster_continuity["value"] == "unknown":
        missing.append("roster_continuity: redraft, keeper, dynasty, best_ball, or dfs")
    if lineup_model["value"] == "active_lineup_unknown_lock":
        missing.append("lineup_lock_model: daily, weekly, best_ball, or no_lock")

    profile["missing_rule_inputs"] = missing
    profile["model_adjustments"] = infer_model_adjustments(profile)

    return profile


def write_csv(profile: Dict[str, Any]) -> None:
    ensure_project_dirs()

    fieldnames = ["field", "value"]
    rows = [
        {"field": "league_name", "value": profile.get("league_name", "")},
        {"field": "season", "value": profile.get("season", "")},
        {"field": "sport", "value": profile.get("sport", "")},
        {"field": "team_count", "value": profile.get("team_count", 0)},
        {"field": "roster_continuity", "value": profile.get("roster_continuity", "")},
        {"field": "league_subtype", "value": profile.get("league_subtype", "")},
        {"field": "lineup_model", "value": profile.get("lineup_model", "")},
        {"field": "lineup_lock_model", "value": profile.get("lineup_lock_model", "")},
        {"field": "scoring_model", "value": profile.get("scoring_model", "")},
        {"field": "scoring_detail", "value": profile.get("scoring_detail", "")},
        {"field": "competition_model", "value": profile.get("competition_model", "")},
        {"field": "planning_horizon", "value": profile.get("planning_horizon", "")},
        {"field": "keeper_count", "value": profile.get("keeper_count", 0)},
        {"field": "contract_model", "value": profile.get("contract_model", "")},
        {"field": "contract_years", "value": profile.get("contract_years", 0)},
        {"field": "historical_seasons", "value": profile.get("historical_seasons", 0)},
        {"field": "asset_classes", "value": ",".join(profile.get("asset_classes", []))},
        {"field": "workspace_rules_loaded", "value": profile.get("workspace_rules_loaded", False)},
    ]

    for item in profile.get("missing_rule_inputs", []):
        rows.append({"field": "missing_rule_input", "value": item})

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(profile: Dict[str, Any]) -> None:
    ensure_project_dirs()
    write_json(OUTPUT_JSON, profile)
    write_csv(profile)


def print_summary(profile: Dict[str, Any]) -> None:
    log_header("League Profile Builder")
    log(f"League: {profile.get('league_name')} ({profile.get('season')})")
    log(f"Sport: {profile.get('sport')}")
    log(f"Teams: {profile.get('team_count')}")
    log(f"Scoring Model: {profile.get('scoring_model')}")
    log(f"Scoring Detail: {profile.get('scoring_detail')}")
    log(f"Roster Continuity: {profile.get('roster_continuity')}")
    log(f"League Subtype: {profile.get('league_subtype')}")
    log(f"Lineup Model: {profile.get('lineup_model')}")
    log(f"Competition Model: {profile.get('competition_model')}")
    log(f"Planning Horizon: {profile.get('planning_horizon')}")
    log(f"Workspace Rules Loaded: {profile.get('workspace_rules_loaded')}")

    if profile.get("missing_rule_inputs"):
        log_section("Missing Rule Inputs")
        for item in profile["missing_rule_inputs"]:
            log(f"  - {item}")

    log("")
    log_section("Output Files")
    log(f"JSON: {OUTPUT_JSON}")
    log(f"CSV: {OUTPUT_CSV}")
    log("Completed successfully.")


def main() -> None:
    profile = build_league_profile()
    write_outputs(profile)
    print_summary(profile)


if __name__ == "__main__":
    main()
