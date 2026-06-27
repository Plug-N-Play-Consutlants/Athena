from __future__ import annotations

import csv
from pathlib import Path
from statistics import mean
from typing import Any

from Core.json_utils import read_json, write_json
from Core.logger import log, log_header, log_section
from Core.project_paths import OUTPUT_DIR


PLAYER_MASTER_PATH = OUTPUT_DIR / "player_master.json"
LEAGUE_PROFILE_PATH = OUTPUT_DIR / "league_profile.json"
ANALYSIS_PROFILE_PATH = OUTPUT_DIR / "analysis_profile.json"
LEAGUE_SETTINGS_PATH = OUTPUT_DIR / "league_settings.json"

OUTPUT_JSON = OUTPUT_DIR / "player_profiles.json"
OUTPUT_CSV = OUTPUT_DIR / "player_profiles.csv"


POSITION_ORDER = ["C", "LW", "RW", "D"]


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _first_present(row: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _normalize_position(value: Any) -> str:
    text = _safe_str(value).upper()
    if not text:
        return "UNKNOWN"

    # Some providers store multiple positions as comma/slash separated text.
    for separator in [",", "/", "|"]:
        if separator in text:
            text = text.split(separator)[0].strip()
            break

    aliases = {
        "CENTER": "C",
        "CENTRE": "C",
        "LEFT WING": "LW",
        "RIGHT WING": "RW",
        "DEFENSE": "D",
        "DEFENCE": "D",
        "DEFENSEMAN": "D",
        "DEFENCEMAN": "D",
    }
    return aliases.get(text, text if text in POSITION_ORDER else text)


def _normalize_player_id(row: dict[str, Any]) -> str:
    return _safe_str(
        _first_present(
            row,
            [
                "asset_id",
                "player_id",
                "playerId",
                "id",
                "fantrax_id",
                "provider_player_id",
            ],
        )
    )


def _normalize_player_name(row: dict[str, Any]) -> str:
    name = _first_present(row, ["player_name", "name", "full_name", "fullName"])
    if name:
        return _safe_str(name)

    first = _safe_str(_first_present(row, ["first_name", "firstName"]))
    last = _safe_str(_first_present(row, ["last_name", "lastName"]))
    return " ".join(part for part in [first, last] if part).strip()


def _normalize_fantasy_team(row: dict[str, Any]) -> str:
    return _safe_str(
        _first_present(
            row,
            [
                "fantasy_team",
                "fantasy_team_name",
                "owner_team",
                "owner_team_name",
                "owner_name",
                "ownerName",
                "team_name",
                "teamName",
                "roster_team",
            ],
        )
    )


def _normalize_fantasy_team_id(row: dict[str, Any]) -> str:
    return _safe_str(
        _first_present(
            row,
            [
                "fantasy_team_id",
                "owner_team_id",
                "owner_id",
                "ownerId",
                "team_id",
                "teamId",
                "roster_team_id",
            ],
        )
    )


def _normalize_nhl_team(row: dict[str, Any]) -> str:
    return _safe_str(
        _first_present(
            row,
            [
                "nhl_team",
                "pro_team",
                "proTeam",
                "team_abbrev",
                "teamAbbrev",
                "team",
            ],
        )
    )


def _extract_points(row: dict[str, Any]) -> float | None:
    return _safe_float(
        _first_present(
            row,
            [
                "points",
                "fantasy_points",
                "fantasyPoints",
                "season_points",
                "seasonPoints",
                "projected_points",
                "projectedPoints",
                "proj_points",
            ],
        )
    )


def _extract_age(row: dict[str, Any]) -> float | None:
    return _safe_float(_first_present(row, ["age", "player_age", "current_age"]))


def _extract_contract_years(row: dict[str, Any]) -> int | None:
    return _safe_int(
        _first_present(
            row,
            [
                "contract_years_remaining",
                "years_remaining",
                "contractYearsRemaining",
                "contract_year",
                "contractYear",
                "contract",
            ],
        )
    )


def _lineup_slots_to_map(value: Any) -> dict[str, int]:
    """Return per-team active lineup slots keyed by normalized position.

    League settings currently stores lineup slots as a list of records:
    [{"position": "C", "active_slots": 3}, ...].
    Some future sources may store them as a dictionary, so this accepts both.
    """
    slots: dict[str, int] = {}

    if isinstance(value, dict):
        for position, count in value.items():
            normalized = _normalize_position(position)
            slots[normalized] = _safe_int(count) or 0
        return slots

    if isinstance(value, list):
        for item in value:
            if not isinstance(item, dict):
                continue
            position = _normalize_position(item.get("position"))
            count = _safe_int(
                _first_present(
                    item,
                    ["active_slots", "max_active", "maxActive", "starter_slots", "slots"],
                )
            ) or 0
            if position and position != "UNKNOWN":
                slots[position] = count

    return slots


def _extract_lineup_slots(league_profile: dict[str, Any], league_settings: dict[str, Any]) -> dict[str, int]:
    profile_slots = _lineup_slots_to_map(league_profile.get("lineup_slots"))
    if profile_slots:
        return profile_slots

    roster = league_settings.get("roster", {}) if isinstance(league_settings, dict) else {}
    settings_slots = _lineup_slots_to_map(roster.get("lineup_slots"))
    return settings_slots


def _build_position_context(
    players: list[dict[str, Any]],
    lineup_slots: dict[str, int],
    team_count: int,
) -> dict[str, dict[str, Any]]:
    counts: dict[str, int] = {}
    for player in players:
        position = _normalize_position(_first_present(player, ["position", "pos", "eligible_positions", "eligiblePositions"]))
        counts[position] = counts.get(position, 0) + 1

    context: dict[str, dict[str, Any]] = {}
    for position, count in counts.items():
        starter_slots_per_team = _safe_int(lineup_slots.get(position)) or 0
        league_starter_slots = starter_slots_per_team * max(team_count, 0)
        scarcity_ratio = league_starter_slots / count if count else 0
        context[position] = {
            "player_count": count,
            "starter_slots": starter_slots_per_team,
            "league_starter_slots": league_starter_slots,
            "scarcity_ratio": round(scarcity_ratio, 4),
        }
    return context


def _score_position_scarcity(position: str, position_context: dict[str, dict[str, Any]]) -> float:
    context = position_context.get(position, {})
    ratio = _safe_float(context.get("scarcity_ratio")) or 0

    # Conservative first-pass scarcity: league starter pressure, bounded 35-75.
    return round(max(35.0, min(75.0, 45.0 + (ratio * 150.0))), 3)


def _score_current_production(points: float | None, all_points: list[float]) -> float | None:
    if points is None or not all_points:
        return None

    max_points = max(all_points)
    min_points = min(all_points)
    if max_points == min_points:
        return 50.0

    normalized = (points - min_points) / (max_points - min_points)
    return round(20.0 + (normalized * 80.0), 3)


def _score_contract(contract_years: int | None, roster_continuity: str) -> float | None:
    if contract_years is None:
        return None

    if roster_continuity == "dynasty":
        if contract_years >= 3:
            return 90.0
        if contract_years == 2:
            return 75.0
        if contract_years == 1:
            return 55.0
        return 35.0

    return 50.0


def _score_future(age: float | None, roster_continuity: str) -> float | None:
    if age is None:
        return None

    if roster_continuity == "dynasty":
        if age <= 22:
            return 92.0
        if age <= 25:
            return 84.0
        if age <= 28:
            return 72.0
        if age <= 31:
            return 58.0
        if age <= 34:
            return 42.0
        return 28.0

    # In non-dynasty contexts, age matters less until decline years.
    if age <= 32:
        return 65.0
    return 45.0


def _availability_status(row: dict[str, Any]) -> str:
    status = _safe_str(_first_present(row, ["status", "injury_status", "injuryStatus"])).lower()
    if not status:
        return "unknown"
    if any(flag in status for flag in ["ir", "inj", "out", "suspended"]):
        return "unavailable_or_limited"
    return status


def _evidence_completeness(profile: dict[str, Any]) -> float:
    checks = [
        bool(profile.get("player_id")),
        bool(profile.get("player_name")),
        profile.get("position") not in (None, "", "UNKNOWN"),
        bool(profile.get("fantasy_team")),
        bool(profile.get("fantasy_team_id")),
        profile.get("current_points") is not None,
        profile.get("age") is not None,
        profile.get("contract_years_remaining") is not None,
    ]
    return round(sum(1 for check in checks if check) / len(checks), 3)


def build_player_profile(row: dict[str, Any], league_profile: dict[str, Any], position_context: dict[str, dict[str, Any]], all_points: list[float]) -> dict[str, Any]:
    position = _normalize_position(_first_present(row, ["position", "pos", "eligible_positions", "eligiblePositions"]))
    points = _extract_points(row)
    age = _extract_age(row)
    contract_years = _extract_contract_years(row)
    roster_continuity = _safe_str(league_profile.get("roster_continuity"))

    profile = {
        "asset_id": _normalize_player_id(row),
        "player_id": _normalize_player_id(row),
        "player_name": _normalize_player_name(row),
        "position": position,
        "fantasy_team": _normalize_fantasy_team(row),
        "fantasy_team_id": _normalize_fantasy_team_id(row),
        "nhl_team": _normalize_nhl_team(row),
        "age": age,
        "current_points": points,
        "contract_years_remaining": contract_years,
        "availability_status": _availability_status(row),
        "keeper_relevance": roster_continuity in {"keeper", "dynasty"},
        "scarcity_score": _score_position_scarcity(position, position_context),
        "current_production_score": _score_current_production(points, all_points),
        "future_score": _score_future(age, roster_continuity),
        "contract_score": _score_contract(contract_years, roster_continuity),
        "position_player_count": position_context.get(position, {}).get("player_count", 0),
        "position_starter_slots": position_context.get(position, {}).get("starter_slots", 0),
        "position_league_starter_slots": position_context.get(position, {}).get("league_starter_slots", 0),
        "position_scarcity_ratio": position_context.get(position, {}).get("scarcity_ratio", 0),
    }
    profile["evidence_completeness"] = _evidence_completeness(profile)
    return profile


def write_profiles_csv(path: Path, profiles: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "asset_id",
        "player_id",
        "player_name",
        "position",
        "fantasy_team",
        "fantasy_team_id",
        "nhl_team",
        "age",
        "current_points",
        "contract_years_remaining",
        "availability_status",
        "keeper_relevance",
        "scarcity_score",
        "current_production_score",
        "future_score",
        "contract_score",
        "position_player_count",
        "position_starter_slots",
        "position_league_starter_slots",
        "position_scarcity_ratio",
        "evidence_completeness",
    ]

    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(profiles)


def build_player_profiles() -> list[dict[str, Any]]:
    log_header("Player Profile Knowledge Builder")

    players = read_json(PLAYER_MASTER_PATH)
    league_profile = read_json(LEAGUE_PROFILE_PATH)
    analysis_profile = read_json(ANALYSIS_PROFILE_PATH)
    league_settings = read_json(LEAGUE_SETTINGS_PATH) if LEAGUE_SETTINGS_PATH.exists() else {}

    if not isinstance(players, list):
        raise ValueError(f"Expected player master list at {PLAYER_MASTER_PATH}")
    if not isinstance(league_profile, dict):
        raise ValueError(f"Expected league profile object at {LEAGUE_PROFILE_PATH}")
    if not isinstance(league_settings, dict):
        league_settings = {}

    lineup_slots = _extract_lineup_slots(league_profile, league_settings)
    team_count = _safe_int(league_profile.get("team_count") or league_settings.get("team_count")) or 0
    position_context = _build_position_context(players, lineup_slots, team_count)
    all_points = [value for value in (_extract_points(row) for row in players) if value is not None]

    profiles = [build_player_profile(row, league_profile, position_context, all_points) for row in players]

    profiles.sort(key=lambda item: (item.get("fantasy_team") or "", item.get("position") or "", item.get("player_name") or ""))

    write_json(OUTPUT_JSON, profiles)
    write_profiles_csv(OUTPUT_CSV, profiles)

    completeness_values = [profile["evidence_completeness"] for profile in profiles]
    avg_completeness = round(mean(completeness_values), 3) if completeness_values else 0

    log(f"League: {league_profile.get('league_name', '')} ({league_profile.get('season', '')})")
    log(f"Sport: {league_profile.get('sport', '')}")
    log(f"Model Key: {analysis_profile.get('model_key', '')}")
    log(f"Players Profiled: {len(profiles)}")
    log(f"Average Evidence Completeness: {avg_completeness}")

    log_section("Position Context")
    for position in POSITION_ORDER:
        context = position_context.get(position, {})
        log(
            f"  {position}: {context.get('player_count', 0)} players | "
            f"{context.get('starter_slots', 0)} starter slots/team | "
            f"{context.get('league_starter_slots', 0)} league starter slots | "
            f"scarcity ratio {context.get('scarcity_ratio', 0)}"
        )

    log_section("Output Files")
    log(f"JSON: {OUTPUT_JSON}")
    log(f"CSV: {OUTPUT_CSV}")
    log("Completed successfully.")

    return profiles


if __name__ == "__main__":
    build_player_profiles()
