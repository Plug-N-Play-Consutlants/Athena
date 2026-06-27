"""
Team Profile Knowledge Builder.

Aggregates canonical player profiles and valuation outputs into deterministic
team-level facts. This module belongs in Knowledge: it does not classify team
direction or make recommendations. It prepares reusable team facts for later
Intelligence modules.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any

from Core.json_utils import read_json, write_json
from Core.logger import log, log_header, log_section
from Core.project_paths import OUTPUT_DIR


PLAYER_PROFILES_PATH = OUTPUT_DIR / "player_profiles.json"
PLAYER_VALUES_PATH = OUTPUT_DIR / "player_values.json"
LEAGUE_PROFILE_PATH = OUTPUT_DIR / "league_profile.json"
ANALYSIS_PROFILE_PATH = OUTPUT_DIR / "analysis_profile.json"

OUTPUT_JSON = OUTPUT_DIR / "team_profiles.json"
OUTPUT_CSV = OUTPUT_DIR / "team_profiles.csv"


POSITION_ORDER = ["C", "LW", "RW", "D"]


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _read_optional_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return read_json(path)
    except Exception:
        return default


def _index_values_by_asset_id(player_values: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for value in player_values:
        asset_id = _safe_str(value.get("asset_id") or value.get("player_id"))
        if asset_id:
            indexed[asset_id] = value
    return indexed


def _extract_lineup_slots(league_profile: dict[str, Any]) -> dict[str, int]:
    raw_slots = (
        league_profile.get("lineup_slots")
        or league_profile.get("roster", {}).get("lineup_slots")
        or league_profile.get("settings", {}).get("lineup_slots")
        or {}
    )

    slots: dict[str, int] = {}

    if isinstance(raw_slots, dict):
        for position, count in raw_slots.items():
            slots[_safe_str(position).upper()] = _safe_int(count)
        return slots

    if isinstance(raw_slots, list):
        for row in raw_slots:
            if not isinstance(row, dict):
                continue
            position = _safe_str(row.get("position") or row.get("slot") or row.get("name")).upper()
            count = _safe_int(row.get("count") or row.get("slots") or row.get("starter_slots"))
            if position:
                slots[position] = count

    return slots


def _get_player_value(value_record: dict[str, Any]) -> float:
    return _safe_float(
        value_record.get("overall_asset_value")
        or value_record.get("overall")
        or value_record.get("asset_value")
        or value_record.get("value")
    )


def _get_dimension(value_record: dict[str, Any], dimension: str) -> float:
    dimensions = value_record.get("dimensions", {})
    if isinstance(dimensions, dict):
        raw = dimensions.get(dimension)
        if isinstance(raw, dict):
            return _safe_float(raw.get("score") or raw.get("value"))
        return _safe_float(raw)
    return 0.0


def _player_asset_id(player: dict[str, Any]) -> str:
    return _safe_str(
        player.get("asset_id")
        or player.get("player_id")
        or player.get("id")
    )


def _player_team_id(player: dict[str, Any]) -> str:
    return _safe_str(
        player.get("fantasy_team_id")
        or player.get("owner_team_id")
        or player.get("team_id")
        or player.get("roster_team_id")
    )


def _player_team_name(player: dict[str, Any]) -> str:
    return _safe_str(
        player.get("fantasy_team")
        or player.get("fantasy_team_name")
        or player.get("owner_team")
        or player.get("owner_team_name")
        or player.get("team_name")
        or player.get("roster_team_name")
    )


def _player_position(player: dict[str, Any]) -> str:
    return _safe_str(
        player.get("primary_position")
        or player.get("position")
        or player.get("pos")
    ).upper()


def _average(values: list[float]) -> float:
    values = [value for value in values if value is not None]
    if not values:
        return 0.0
    return round(sum(values) / len(values), 3)


def _round(value: float) -> float:
    return round(float(value), 3)


def _build_empty_position_counts() -> dict[str, int]:
    return {position: 0 for position in POSITION_ORDER}


def _build_team_profile(
    team_key: str,
    team_name: str,
    players: list[dict[str, Any]],
    values_by_asset_id: dict[str, dict[str, Any]],
    lineup_slots: dict[str, int],
    league_profile: dict[str, Any],
    analysis_profile: dict[str, Any],
) -> dict[str, Any]:
    position_counts = _build_empty_position_counts()
    position_values: dict[str, list[float]] = {position: [] for position in POSITION_ORDER}

    asset_values: list[float] = []
    current_values: list[float] = []
    future_values: list[float] = []
    contract_values: list[float] = []
    scarcity_values: list[float] = []
    risk_values: list[float] = []
    confidence_values: list[float] = []
    evidence_values: list[float] = []

    player_summaries: list[dict[str, Any]] = []

    for player in players:
        asset_id = _player_asset_id(player)
        position = _player_position(player)
        if position in position_counts:
            position_counts[position] += 1

        value_record = values_by_asset_id.get(asset_id, {})
        asset_value = _get_player_value(value_record)
        confidence = _safe_float(value_record.get("confidence"))
        evidence_completeness = _safe_float(player.get("evidence_completeness"))

        asset_values.append(asset_value)
        current_values.append(_get_dimension(value_record, "current"))
        future_values.append(_get_dimension(value_record, "future"))
        contract_values.append(_get_dimension(value_record, "contract"))
        scarcity_values.append(_get_dimension(value_record, "scarcity"))
        risk_values.append(_get_dimension(value_record, "risk"))
        confidence_values.append(confidence)
        evidence_values.append(evidence_completeness)

        if position in position_values:
            position_values[position].append(asset_value)

        player_summaries.append(
            {
                "asset_id": asset_id,
                "player_name": _safe_str(player.get("player_name") or player.get("name")),
                "position": position,
                "asset_value": _round(asset_value),
                "confidence": _round(confidence),
            }
        )

    roster_size = len(players)
    total_asset_value = _round(sum(asset_values))
    average_asset_value = _average(asset_values)

    position_depth: dict[str, dict[str, Any]] = {}
    for position in POSITION_ORDER:
        count = position_counts.get(position, 0)
        starter_slots = _safe_int(lineup_slots.get(position))
        depth_margin = count - starter_slots
        position_depth[position] = {
            "rostered": count,
            "starter_slots_per_team": starter_slots,
            "depth_margin": depth_margin,
            "average_asset_value": _average(position_values.get(position, [])),
            "coverage_ratio": _round(count / starter_slots) if starter_slots else 0.0,
        }

    ranked_players = sorted(
        player_summaries,
        key=lambda row: (row.get("asset_value", 0), row.get("player_name", "")),
        reverse=True,
    )

    return {
        "team_id": team_key,
        "team_name": team_name,
        "league_id": _safe_str(league_profile.get("league_id")),
        "season": league_profile.get("season"),
        "sport": _safe_str(league_profile.get("sport")),
        "model_key": _safe_str(analysis_profile.get("model_key")),
        "roster_size": roster_size,
        "position_counts": position_counts,
        "position_depth": position_depth,
        "total_asset_value": total_asset_value,
        "average_asset_value": average_asset_value,
        "valuation_dimensions": {
            "current_average": _average(current_values),
            "future_average": _average(future_values),
            "contract_average": _average(contract_values),
            "scarcity_average": _average(scarcity_values),
            "risk_average": _average(risk_values),
        },
        "confidence": _average(confidence_values),
        "evidence_completeness": _average(evidence_values),
        "top_assets": ranked_players[:10],
        "evidence": [
            f"Roster contains {roster_size} profiled players.",
            f"Total preliminary asset value is {total_asset_value}.",
            f"Average preliminary asset value is {average_asset_value}.",
            "Team profile is deterministic and based on current player profile and valuation outputs.",
        ],
        "limitations": [
            "Production, age, contract, injury, and relationship inputs remain limited until additional Knowledge builders are added.",
            "Team direction is intentionally not classified in this Knowledge module.",
        ],
    }


def build_team_profiles() -> list[dict[str, Any]]:
    log_header("Team Profile Knowledge Builder")

    player_profiles = _read_optional_json(PLAYER_PROFILES_PATH, [])
    player_values = _read_optional_json(PLAYER_VALUES_PATH, [])
    league_profile = _read_optional_json(LEAGUE_PROFILE_PATH, {})
    analysis_profile = _read_optional_json(ANALYSIS_PROFILE_PATH, {})

    if not isinstance(player_profiles, list):
        raise ValueError("player_profiles.json must contain a list of player profile records.")
    if not isinstance(player_values, list):
        raise ValueError("player_values.json must contain a list of valuation records.")

    values_by_asset_id = _index_values_by_asset_id(player_values)
    lineup_slots = _extract_lineup_slots(league_profile)

    grouped_players: dict[str, list[dict[str, Any]]] = defaultdict(list)
    team_names: dict[str, str] = {}

    for player in player_profiles:
        if not isinstance(player, dict):
            continue

        team_id = _player_team_id(player)
        team_name = _player_team_name(player)

        if not team_id and not team_name:
            team_id = "UNASSIGNED"
            team_name = "Unassigned"
        elif not team_id:
            team_id = team_name
        elif not team_name:
            team_name = team_id

        grouped_players[team_id].append(player)
        team_names[team_id] = team_name

    team_profiles = [
        _build_team_profile(
            team_key=team_id,
            team_name=team_names.get(team_id, team_id),
            players=players,
            values_by_asset_id=values_by_asset_id,
            lineup_slots=lineup_slots,
            league_profile=league_profile,
            analysis_profile=analysis_profile,
        )
        for team_id, players in grouped_players.items()
    ]

    team_profiles.sort(key=lambda row: (row.get("team_name") or "", row.get("team_id") or ""))

    write_json(OUTPUT_JSON, team_profiles)
    write_team_profiles_csv(OUTPUT_CSV, team_profiles)

    log(f"League: {_safe_str(league_profile.get('league_name') or league_profile.get('name'))} ({league_profile.get('season')})")
    log(f"Sport: {_safe_str(league_profile.get('sport'))}")
    log(f"Model Key: {_safe_str(analysis_profile.get('model_key'))}")
    log(f"Teams Profiled: {len(team_profiles)}")
    log(f"Players Assigned: {sum(_safe_int(team.get('roster_size')) for team in team_profiles)}")
    log(f"Average Team Value: {_average([_safe_float(team.get('total_asset_value')) for team in team_profiles])}")
    log(f"Average Team Confidence: {_average([_safe_float(team.get('confidence')) for team in team_profiles])}")

    log_section("Top Preliminary Team Values")
    for team in sorted(team_profiles, key=lambda row: _safe_float(row.get("total_asset_value")), reverse=True)[:10]:
        log(
            f"  {team.get('team_name')}: "
            f"{team.get('total_asset_value')} | "
            f"roster {team.get('roster_size')} | "
            f"confidence {team.get('confidence')}"
        )

    log_section("Output Files")
    log(f"JSON: {OUTPUT_JSON}")
    log(f"CSV: {OUTPUT_CSV}")
    log("Completed successfully.")

    return team_profiles


def write_team_profiles_csv(path: Path, team_profiles: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "team_id",
        "team_name",
        "league_id",
        "season",
        "sport",
        "model_key",
        "roster_size",
        "total_asset_value",
        "average_asset_value",
        "current_average",
        "future_average",
        "contract_average",
        "scarcity_average",
        "risk_average",
        "confidence",
        "evidence_completeness",
        "count_c",
        "count_lw",
        "count_rw",
        "count_d",
        "depth_c",
        "depth_lw",
        "depth_rw",
        "depth_d",
    ]

    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for team in team_profiles:
            dimensions = team.get("valuation_dimensions", {}) or {}
            position_counts = team.get("position_counts", {}) or {}
            position_depth = team.get("position_depth", {}) or {}

            writer.writerow(
                {
                    "team_id": team.get("team_id"),
                    "team_name": team.get("team_name"),
                    "league_id": team.get("league_id"),
                    "season": team.get("season"),
                    "sport": team.get("sport"),
                    "model_key": team.get("model_key"),
                    "roster_size": team.get("roster_size"),
                    "total_asset_value": team.get("total_asset_value"),
                    "average_asset_value": team.get("average_asset_value"),
                    "current_average": dimensions.get("current_average"),
                    "future_average": dimensions.get("future_average"),
                    "contract_average": dimensions.get("contract_average"),
                    "scarcity_average": dimensions.get("scarcity_average"),
                    "risk_average": dimensions.get("risk_average"),
                    "confidence": team.get("confidence"),
                    "evidence_completeness": team.get("evidence_completeness"),
                    "count_c": position_counts.get("C", 0),
                    "count_lw": position_counts.get("LW", 0),
                    "count_rw": position_counts.get("RW", 0),
                    "count_d": position_counts.get("D", 0),
                    "depth_c": (position_depth.get("C", {}) or {}).get("depth_margin", 0),
                    "depth_lw": (position_depth.get("LW", {}) or {}).get("depth_margin", 0),
                    "depth_rw": (position_depth.get("RW", {}) or {}).get("depth_margin", 0),
                    "depth_d": (position_depth.get("D", {}) or {}).get("depth_margin", 0),
                }
            )


if __name__ == "__main__":
    build_team_profiles()
