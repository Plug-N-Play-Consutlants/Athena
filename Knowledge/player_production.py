"""
Player Production Knowledge Builder.

Normalizes player production into canonical Knowledge-layer outputs.

Preferred automated path:
    Raw/nhl_skater_summary.json
    Output/player_identity_map.json

Fallback paths:
    Raw/player_production.csv
    Raw/player_production.json
    Raw/player_stats.json

Outputs:
    Output/player_production.json
    Output/player_production.csv
    Output/player_production_import_template.csv when no source exists

Layer rule:
    This module does not fetch data and does not perform valuation. It converts
    available production facts into canonical Knowledge for Intelligence modules.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from Core.json_utils import read_json, read_optional_json, write_json
from Core.logger import log, log_header, log_section
from Core.project_paths import OUTPUT_DIR, RAW_DIR

PLAYER_MASTER_JSON = OUTPUT_DIR / "player_master.json"
IDENTITY_MAP_JSON = OUTPUT_DIR / "player_identity_map.json"
NHL_SKATER_SUMMARY_JSON = RAW_DIR / "nhl_skater_summary.json"

INPUT_CSV = RAW_DIR / "player_production.csv"
INPUT_JSON = RAW_DIR / "player_production.json"
INPUT_FANTRAX_STATS_JSON = RAW_DIR / "player_stats.json"

OUTPUT_JSON = OUTPUT_DIR / "player_production.json"
OUTPUT_CSV = OUTPUT_DIR / "player_production.csv"
OUTPUT_TEMPLATE_CSV = OUTPUT_DIR / "player_production_import_template.csv"

FIELDNAMES = [
    "player_id",
    "player_name",
    "nhl_player_id",
    "nhl_player_name",
    "season",
    "nhl_team",
    "position",
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
    "games_with_points",
    "scoring_frequency",
    "source",
    "source_status",
    "match_confidence",
    "evidence_completeness",
]

TEMPLATE_FIELDNAMES = [
    "player_id",
    "player_name",
    "season",
    "games_played",
    "goals",
    "assists",
    "points",
    "games_with_points",
]

ALIASES = {
    "player_id": ["player_id", "id", "playerid", "playerId", "fantrax_id", "provider_player_id"],
    "player_name": ["player_name", "name", "player", "full_name", "fullName"],
    "season": ["season", "year", "season_year", "seasonYear", "seasonId"],
    "games_played": ["games_played", "gp", "games", "gamesPlayed"],
    "goals": ["goals", "g"],
    "assists": ["assists", "a"],
    "points": ["points", "pts", "p", "fantasy_points", "fantasyPoints", "fp", "score"],
    "games_with_points": ["games_with_points", "gamesWithPoints", "scoring_games", "point_games"],
}


def _safe_str(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _safe_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_key(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


def _normalize_name(value: str) -> str:
    return _safe_str(value).lower().replace(".", "").replace(",", "").strip()


def _get_alias(row: dict[str, Any], canonical_key: str) -> Any:
    normalized_row = {_normalize_key(str(key)): value for key, value in row.items()}
    for alias in ALIASES.get(canonical_key, [canonical_key]):
        value = row.get(alias)
        if value not in (None, ""):
            return value
        value = normalized_row.get(_normalize_key(alias))
        if value not in (None, ""):
            return value
    return None


def _extract_player_id(player: dict[str, Any]) -> str:
    return _safe_str(
        player.get("player_id")
        or player.get("id")
        or player.get("provider_player_id")
        or player.get("fantrax_id")
        or player.get("fantrax_player_id")
    )


def _extract_player_name(player: dict[str, Any]) -> str:
    return _safe_str(
        player.get("player_name")
        or player.get("name")
        or player.get("full_name")
        or player.get("fullName")
        or player.get("fantrax_player_name")
        or player.get("canonical_player_name")
    )


def _load_list_json(path: Path) -> list[dict[str, Any]]:
    payload = read_optional_json(path)
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("players", "player_master", "records", "data", "items", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    return []


def _load_player_master() -> list[dict[str, Any]]:
    payload = read_json(PLAYER_MASTER_JSON)
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("players", "player_master", "records", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    return []


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", newline="", encoding="utf-8-sig") as csv_file:
        return [dict(row) for row in csv.DictReader(csv_file)]


def _flatten_rows(payload: Any) -> list[dict[str, Any]]:
    """Recursively extract list-like records from unknown provider JSON."""
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]

    if not isinstance(payload, dict):
        return []

    preferred_keys = (
        "players", "stats", "playerStats", "player_stats", "records", "data",
        "items", "results", "scorers", "rows", "tableRows",
    )
    for key in preferred_keys:
        value = payload.get(key)
        if isinstance(value, list):
            extracted = [row for row in value if isinstance(row, dict)]
            if extracted:
                return extracted
        if isinstance(value, dict):
            extracted = _flatten_rows(value)
            if extracted:
                return extracted

    dict_values = [value for value in payload.values() if isinstance(value, dict)]
    if dict_values:
        player_like = []
        for key, value in payload.items():
            if not isinstance(value, dict):
                continue
            row = dict(value)
            if "player_id" not in row and "id" not in row and "playerId" not in row:
                row["player_id"] = key
            player_like.append(row)
        return player_like

    return []


def _calculate_points(goals: int | None, assists: int | None, points: int | None) -> int | None:
    if points is not None:
        return points
    if goals is not None or assists is not None:
        return (goals or 0) + (assists or 0)
    return None


def _calculate_ppg(points: int | None, games_played: int | None) -> float | None:
    if points is None or not games_played:
        return None
    return round(points / games_played, 4)


def _calculate_scoring_frequency(games_with_points: int | None, games_played: int | None) -> float | None:
    if games_with_points is None or not games_played:
        return None
    return round(games_with_points / games_played, 4)


def _evidence_completeness(record: dict[str, Any]) -> float:
    required = [
        "player_id", "player_name", "season", "games_played", "goals", "assists",
        "points", "points_per_game", "nhl_player_id", "nhl_team", "position",
    ]
    present = sum(1 for key in required if record.get(key) not in (None, ""))
    return round(present / len(required), 3)


def _build_player_lookup(players: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_id: dict[str, dict[str, Any]] = {}
    by_name: dict[str, dict[str, Any]] = {}
    for player in players:
        player_id = _extract_player_id(player)
        player_name = _extract_player_name(player)
        if player_id:
            by_id[player_id] = player
        if player_name:
            by_name[_normalize_name(player_name)] = player
    return by_id, by_name


def _load_nhl_stats_by_id() -> dict[str, dict[str, Any]]:
    payload = read_optional_json(NHL_SKATER_SUMMARY_JSON)
    if payload is None:
        return {}
    rows = _flatten_rows(payload)
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        nhl_player_id = _safe_str(row.get("playerId") or row.get("player_id") or row.get("id"))
        if nhl_player_id:
            by_id[nhl_player_id] = row
    return by_id


def _normalize_nhl_record(identity: dict[str, Any], nhl_row: dict[str, Any]) -> dict[str, Any]:
    goals = _safe_int(nhl_row.get("goals"))
    assists = _safe_int(nhl_row.get("assists"))
    points = _calculate_points(goals, assists, _safe_int(nhl_row.get("points")))
    games_played = _safe_int(nhl_row.get("gamesPlayed"))
    ppg = _safe_float(nhl_row.get("pointsPerGame"))
    if ppg is None:
        ppg = _calculate_ppg(points, games_played)

    record = {
        "player_id": _safe_str(identity.get("fantrax_player_id")),
        "player_name": _safe_str(identity.get("canonical_player_name") or identity.get("fantrax_player_name")),
        "nhl_player_id": _safe_str(identity.get("nhl_player_id")),
        "nhl_player_name": _safe_str(nhl_row.get("skaterFullName") or identity.get("nhl_player_name")),
        "season": _safe_int(nhl_row.get("seasonId")),
        "nhl_team": _safe_str(nhl_row.get("teamAbbrevs") or identity.get("nhl_team")),
        "position": _safe_str(nhl_row.get("positionCode") or identity.get("nhl_position") or identity.get("fantrax_position")),
        "games_played": games_played,
        "goals": goals,
        "assists": assists,
        "points": points,
        "points_per_game": round(ppg, 4) if ppg is not None else None,
        "shots": _safe_int(nhl_row.get("shots")),
        "shooting_pct": _safe_float(nhl_row.get("shootingPct")),
        "power_play_goals": _safe_int(nhl_row.get("ppGoals")),
        "power_play_points": _safe_int(nhl_row.get("ppPoints")),
        "short_handed_goals": _safe_int(nhl_row.get("shGoals")),
        "short_handed_points": _safe_int(nhl_row.get("shPoints")),
        "even_strength_goals": _safe_int(nhl_row.get("evGoals")),
        "even_strength_points": _safe_int(nhl_row.get("evPoints")),
        "time_on_ice_per_game_seconds": _safe_float(nhl_row.get("timeOnIcePerGame")),
        "current_production_score": None,
        "production_rank": None,
        "production_percentile": None,
        "games_with_points": None,
        "scoring_frequency": None,
        "source": "nhl_skater_summary",
        "source_status": "matched",
        "match_confidence": _safe_float(identity.get("match_confidence")),
        "evidence_completeness": 0.0,
    }
    record["evidence_completeness"] = _evidence_completeness(record)
    return record


def _load_from_nhl_identity_bridge() -> tuple[list[dict[str, Any]], str]:
    identities = _load_list_json(IDENTITY_MAP_JSON)
    nhl_by_id = _load_nhl_stats_by_id()
    if not identities or not nhl_by_id:
        return [], "missing"

    records: list[dict[str, Any]] = []
    for identity in identities:
        status = _safe_str(identity.get("resolution_status"))
        nhl_player_id = _safe_str(identity.get("nhl_player_id"))
        if status not in ("resolved", "review") or not nhl_player_id:
            continue
        nhl_row = nhl_by_id.get(nhl_player_id)
        if not nhl_row:
            continue
        records.append(_normalize_nhl_record(identity, nhl_row))

    return records, "nhl_identity_bridge" if records else "missing"


def _normalize_manual_row(
    row: dict[str, Any],
    source: str,
    players_by_id: dict[str, dict[str, Any]],
    players_by_name: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    source_player_id = _safe_str(_get_alias(row, "player_id"))
    source_player_name = _safe_str(_get_alias(row, "player_name"))

    matched_player = players_by_id.get(source_player_id) if source_player_id else None
    if matched_player is None and source_player_name:
        matched_player = players_by_name.get(_normalize_name(source_player_name))

    player_id = _extract_player_id(matched_player or {}) or source_player_id
    player_name = _extract_player_name(matched_player or {}) or source_player_name

    games_played = _safe_int(_get_alias(row, "games_played"))
    goals = _safe_int(_get_alias(row, "goals"))
    assists = _safe_int(_get_alias(row, "assists"))
    points = _calculate_points(goals, assists, _safe_int(_get_alias(row, "points")))
    points_per_game = _calculate_ppg(points, games_played)
    games_with_points = _safe_int(_get_alias(row, "games_with_points"))
    scoring_frequency = _calculate_scoring_frequency(games_with_points, games_played)

    record = {
        "player_id": player_id,
        "player_name": player_name,
        "nhl_player_id": "",
        "nhl_player_name": "",
        "season": _safe_int(_get_alias(row, "season")),
        "nhl_team": _safe_str((matched_player or {}).get("nhl_team")),
        "position": _safe_str((matched_player or {}).get("position")),
        "games_played": games_played,
        "goals": goals,
        "assists": assists,
        "points": points,
        "points_per_game": points_per_game,
        "shots": None,
        "shooting_pct": None,
        "power_play_goals": None,
        "power_play_points": None,
        "short_handed_goals": None,
        "short_handed_points": None,
        "even_strength_goals": None,
        "even_strength_points": None,
        "time_on_ice_per_game_seconds": None,
        "current_production_score": None,
        "production_rank": None,
        "production_percentile": None,
        "games_with_points": games_with_points,
        "scoring_frequency": scoring_frequency,
        "source": source,
        "source_status": "matched" if matched_player else "unmatched",
        "match_confidence": 1.0 if matched_player else 0.0,
        "evidence_completeness": 0.0,
    }
    record["evidence_completeness"] = _evidence_completeness(record)
    return record


def _load_manual_rows() -> tuple[list[dict[str, Any]], str]:
    if INPUT_CSV.exists():
        return _read_csv_rows(INPUT_CSV), "csv"

    payload = read_optional_json(INPUT_JSON)
    if payload is not None:
        rows = _flatten_rows(payload)
        if rows:
            return rows, "json"

    fantrax_payload = read_optional_json(INPUT_FANTRAX_STATS_JSON)
    if fantrax_payload is not None:
        rows = _flatten_rows(fantrax_payload)
        if rows:
            return rows, "fantrax_player_stats"

    return [], "missing"


def _apply_production_scores(records: list[dict[str, Any]]) -> None:
    scored = [row for row in records if row.get("points") is not None]
    if not scored:
        return

    points_values = sorted({float(row.get("points") or 0) for row in scored})
    ppg_values = sorted({float(row.get("points_per_game") or 0) for row in scored})

    def percentile(value: float, values: list[float]) -> float:
        if not values:
            return 0.5
        if len(values) == 1:
            return 1.0
        below_or_equal = sum(1 for item in values if item <= value)
        return below_or_equal / len(values)

    ranked = sorted(scored, key=lambda row: (row.get("points") or 0, row.get("points_per_game") or 0), reverse=True)
    for index, row in enumerate(ranked, start=1):
        points = float(row.get("points") or 0)
        ppg = float(row.get("points_per_game") or 0)
        points_pct = percentile(points, points_values)
        ppg_pct = percentile(ppg, ppg_values)
        production_percentile = round((points_pct * 0.72) + (ppg_pct * 0.28), 4)
        row["production_rank"] = index
        row["production_percentile"] = production_percentile
        row["current_production_score"] = round(production_percentile * 100, 3)


def _write_csv(path: Path, records: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow({key: record.get(key) for key in fieldnames})


def _write_import_template(players: list[dict[str, Any]]) -> None:
    rows = []
    for player in players:
        rows.append(
            {
                "player_id": _extract_player_id(player),
                "player_name": _extract_player_name(player),
                "season": "",
                "games_played": "",
                "goals": "",
                "assists": "",
                "points": "",
                "games_with_points": "",
            }
        )
    _write_csv(OUTPUT_TEMPLATE_CSV, rows, TEMPLATE_FIELDNAMES)


def build_player_production() -> list[dict[str, Any]]:
    log_header("Player Production Knowledge Builder")

    players = _load_player_master()
    players_by_id, players_by_name = _build_player_lookup(players)

    records, source = _load_from_nhl_identity_bridge()

    if source == "missing":
        raw_rows, manual_source = _load_manual_rows()
        source = manual_source
        if manual_source == "missing":
            records = []
            _write_import_template(players)
            log("No production source found.")
            log(f"Created import template: {OUTPUT_TEMPLATE_CSV}")
        else:
            records = [
                _normalize_manual_row(row, manual_source, players_by_id, players_by_name)
                for row in raw_rows
            ]

    _apply_production_scores(records)
    records.sort(key=lambda row: (row.get("production_rank") or 99999, row.get("player_name") or ""))

    write_json(OUTPUT_JSON, records)
    _write_csv(OUTPUT_CSV, records, FIELDNAMES)

    matched = sum(1 for row in records if row.get("source_status") == "matched")
    unmatched = sum(1 for row in records if row.get("source_status") == "unmatched")
    avg_completeness = round(sum(float(row.get("evidence_completeness") or 0) for row in records) / len(records), 3) if records else 0.0

    log(f"Player Master Records: {len(players)}")
    log(f"Production Source: {source}")
    log(f"Production Rows: {len(records)}")
    log(f"Matched Rows: {matched}")
    log(f"Unmatched Rows: {unmatched}")
    log(f"Average Evidence Completeness: {avg_completeness}")

    if records:
        log_section("Top Point Producers")
        top_rows = sorted(records, key=lambda row: (row.get("points") or 0, row.get("points_per_game") or 0), reverse=True)[:10]
        for row in top_rows:
            log(
                f"  {row.get('player_name')}: {row.get('points')} pts | "
                f"{row.get('points_per_game')} PPG | score {row.get('current_production_score')} | "
                f"completeness {row.get('evidence_completeness')}"
            )

    missing_identity_count = max(len(players) - len(records), 0)
    if missing_identity_count:
        log_section("Coverage Note")
        log(f"  {missing_identity_count} player master records do not currently have production rows.")
        log("  This is expected for unresolved identities, inactive players, or skaters missing from the NHL summary feed.")

    log_section("Output Files")
    log(f"JSON: {OUTPUT_JSON}")
    log(f"CSV: {OUTPUT_CSV}")
    if source == "missing":
        log(f"Template: {OUTPUT_TEMPLATE_CSV}")
    log("Completed successfully.")

    return records


if __name__ == "__main__":
    build_player_production()
