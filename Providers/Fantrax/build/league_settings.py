# -*- coding: utf-8 -*-
"""
Fantrax league settings builder.

Build-layer responsibility:
- Read provider-specific Fantrax league info from Raw/league_info.json.
- Normalize it into a provider-neutral league settings document.

Inputs:
- Raw/league_info.json

Outputs:
- Output/league_settings.json
- Output/league_settings.csv
"""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import csv
from typing import Any, Dict, List

from Core.json_utils import read_json, write_json
from Core.logger import log, log_header, log_section
from Core.project_paths import RAW_DIR, OUTPUT_DIR, ensure_project_dirs


GENERATOR_NAME = "Providers.Fantrax.build.league_settings"
GENERATOR_VERSION = "2.0.0"
PROVIDER = "fantrax"

RAW_LEAGUE_INFO = RAW_DIR / "league_info.json"
OUTPUT_JSON = OUTPUT_DIR / "league_settings.json"
OUTPUT_CSV = OUTPUT_DIR / "league_settings.csv"


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


def load_league_info() -> Dict[str, Any]:
    payload = read_json(RAW_LEAGUE_INFO)

    if isinstance(payload, dict) and "error" in payload:
        error = payload.get("error", {})
        code = error.get("code", "ERROR")
        message = error.get("message", "Unknown provider error")
        raise ValueError(f"Raw league_info.json contains provider error: {code} - {message}")

    if not isinstance(payload, dict):
        raise TypeError("Raw league_info.json must contain a JSON object.")

    return payload


def normalize_lineup_slots(roster_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    constraints = roster_info.get("positionConstraints", {})
    slots: List[Dict[str, Any]] = []

    if not isinstance(constraints, dict):
        return slots

    for position, rules in sorted(constraints.items()):
        if not isinstance(rules, dict):
            rules = {}

        slots.append(
            {
                "position": safe_str(position),
                "active_slots": safe_int(rules.get("maxActive")),
                "min_active": safe_int(rules.get("minActive")),
                "max_active": safe_int(rules.get("maxActive")),
            }
        )

    return slots


def normalize_scoring_categories(scoring_system: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    category_settings = scoring_system.get("scoringCategorySettings", [])

    if not isinstance(category_settings, list):
        return rows

    for group_block in category_settings:
        if not isinstance(group_block, dict):
            continue

        group = group_block.get("group", {}) or {}
        configs = group_block.get("configs", []) or []

        if not isinstance(configs, list):
            continue

        for config in configs:
            if not isinstance(config, dict):
                continue

            scoring_category = config.get("scoringCategory", {}) or {}
            position = config.get("position", {}) or {}

            rows.append(
                {
                    "group_code": safe_str(group.get("code")),
                    "group_name": safe_str(group.get("name")),
                    "category_code": safe_str(scoring_category.get("code")),
                    "category_name": safe_str(scoring_category.get("name")),
                    "category_short_name": safe_str(scoring_category.get("shortName")),
                    "position_code": safe_str(position.get("code")),
                    "position_name": safe_str(position.get("name")),
                    "points": float(config.get("points", 0) or 0),
                    "cumulative": bool(config.get("cumulative", False)),
                }
            )

    return rows


def build_league_settings() -> Dict[str, Any]:
    league = load_league_info()
    roster_info = league.get("rosterInfo", {}) or {}
    scoring_system = league.get("scoringSystem", {}) or {}
    team_info = league.get("teamInfo", {}) or {}
    draft_settings = league.get("draftSettings", {}) or {}

    lineup_slots = normalize_lineup_slots(roster_info)
    scoring_categories = normalize_scoring_categories(scoring_system)

    active_slots = sum(slot["active_slots"] for slot in lineup_slots)

    return {
        "league_id": safe_str(league.get("leagueHistoryId")),
        "league_name": safe_str(league.get("leagueName")),
        "season": safe_int(league.get("seasonYear")),
        "sport": "NHL",
        "provider": PROVIDER,
        "start_date": safe_str(league.get("startDate")),
        "end_date": safe_str(league.get("endDate")),
        "team_count": len(team_info) if isinstance(team_info, dict) else 0,
        "draft": {
            "type": safe_str(league.get("draftType") or draft_settings.get("draftType")),
        },
        "roster": {
            "lineup_slots": lineup_slots,
            "max_total_players": safe_int(roster_info.get("maxTotalPlayers")),
            "max_total_active_players": safe_int(roster_info.get("maxTotalActivePlayers"), active_slots),
            "max_total_reserve_players": safe_int(roster_info.get("maxTotalReservePlayers")),
        },
        "scoring": {
            "type": safe_str(scoring_system.get("type")),
            "categories": scoring_categories,
        },
        "teams": [
            {
                "team_id": safe_str(team.get("id") if isinstance(team, dict) else team_id),
                "team_name": safe_str(team.get("name") if isinstance(team, dict) else team_id),
            }
            for team_id, team in sorted(team_info.items())
        ] if isinstance(team_info, dict) else [],
        "source": {
            "raw_file": str(RAW_LEAGUE_INFO),
            "generator": GENERATOR_NAME,
            "generator_version": GENERATOR_VERSION,
        },
    }


def write_csv(settings: Dict[str, Any]) -> None:
    ensure_project_dirs()

    fieldnames = ["setting", "value"]
    rows = [
        {"setting": "league_id", "value": settings.get("league_id", "")},
        {"setting": "league_name", "value": settings.get("league_name", "")},
        {"setting": "season", "value": settings.get("season", "")},
        {"setting": "sport", "value": settings.get("sport", "")},
        {"setting": "provider", "value": settings.get("provider", "")},
        {"setting": "team_count", "value": settings.get("team_count", "")},
        {"setting": "draft_type", "value": settings.get("draft", {}).get("type", "")},
        {"setting": "scoring_type", "value": settings.get("scoring", {}).get("type", "")},
        {"setting": "max_total_players", "value": settings.get("roster", {}).get("max_total_players", "")},
        {"setting": "max_total_active_players", "value": settings.get("roster", {}).get("max_total_active_players", "")},
        {"setting": "max_total_reserve_players", "value": settings.get("roster", {}).get("max_total_reserve_players", "")},
    ]

    for slot in settings.get("roster", {}).get("lineup_slots", []):
        rows.append({"setting": f"active_slots_{slot['position']}", "value": slot.get("active_slots", 0)})

    for category in settings.get("scoring", {}).get("categories", []):
        rows.append(
            {
                "setting": f"scoring_{category.get('category_short_name') or category.get('category_code')}",
                "value": category.get("points", 0),
            }
        )

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(settings: Dict[str, Any]) -> None:
    ensure_project_dirs()
    write_json(OUTPUT_JSON, settings)
    write_csv(settings)


def print_summary(settings: Dict[str, Any]) -> None:
    log_header("League Settings Builder")
    log(f"League: {settings.get('league_name')} ({settings.get('season')})")
    log(f"Sport: {settings.get('sport')}")
    log(f"Teams: {settings.get('team_count')}")
    log(f"Scoring: {settings.get('scoring', {}).get('type')}")
    log(f"Draft: {settings.get('draft', {}).get('type')}")

    log_section("Lineup Slots")
    for slot in settings.get("roster", {}).get("lineup_slots", []):
        log(f"  {slot['position']}: {slot['active_slots']}")

    log("")
    log_section("Output Files")
    log(f"JSON: {OUTPUT_JSON}")
    log(f"CSV: {OUTPUT_CSV}")
    log("Completed successfully.")


def main() -> None:
    settings = build_league_settings()
    write_outputs(settings)
    print_summary(settings)


if __name__ == "__main__":
    main()
