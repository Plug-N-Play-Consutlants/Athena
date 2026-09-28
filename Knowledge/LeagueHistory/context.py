"""Build an isolated, season-scoped historical league context.

Historical contexts are evidence layers. They never replace or mutate the active
workspace. Player production preserves games played and defines fantasy PPG as
Points Per Game; power-play goals must use an explicit power_play_goals field.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "Configuration" / "historical_leagues.json"


def load_historical_registry(path: Path = REGISTRY) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def historical_entry(season: int, path: Path = REGISTRY) -> dict[str, Any]:
    data = load_historical_registry(path)
    for item in data.get("historical_leagues", []):
        if int(item.get("season", 0)) == int(season):
            return dict(item)
    raise KeyError(f"No historical league registered for season {season}.")


def _walk_dicts(node: Any):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk_dicts(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk_dicts(value)


def _first(row: dict[str, Any], *keys: str) -> Any:
    lowered = {str(k).lower(): v for k, v in row.items()}
    for key in keys:
        if key.lower() in lowered and lowered[key.lower()] not in (None, ""):
            return lowered[key.lower()]
    return None


def _number(value: Any) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def extract_player_season_stats(payload: Any) -> list[dict[str, Any]]:
    """Conservatively normalize only rows exposing identity plus GP/point facts."""
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, float | None, float | None]] = set()
    for row in _walk_dicts(payload):
        name = _first(row, "playerName", "player_name", "name")
        player_id = _first(row, "playerId", "player_id", "fantraxId", "id")
        gp = _number(_first(row, "gamesPlayed", "games_played", "GP", "gp"))
        goals = _number(_first(row, "goals", "G", "g"))
        assists = _number(_first(row, "assists", "A", "a"))
        points = _number(_first(row, "points", "PTS", "pts", "P", "p"))
        if not (name or player_id) or gp is None:
            continue
        if points is None and goals is not None and assists is not None:
            points = goals + assists
        ppg = (points / gp) if points is not None and gp > 0 else None
        key = (str(player_id or name), gp, points)
        if key in seen:
            continue
        seen.add(key)
        records.append({
            "player_id": player_id,
            "player_name": name,
            "games_played": gp,
            "goals": goals,
            "assists": assists,
            "points": points,
            "points_per_game": ppg,
            "ppg_semantic": "points_per_game",
        })
    return records


def build_historical_context(
    *,
    season: int,
    league_id: str,
    raw_payloads: dict[str, Any],
    source_provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stats_payload = raw_payloads.get("player_stats")
    player_stats = extract_player_season_stats(stats_payload) if stats_payload is not None else []
    return {
        "schema": "athena.historical_league_context.v1",
        "season": int(season),
        "league_id": str(league_id),
        "provider": "Fantrax",
        "scope": "historical_read_only",
        "active_workspace_mutation_allowed": False,
        "production_normalization": {
            "games_played_is_first_class": True,
            "fantasy_ppg": "points_per_game",
            "power_play_goals_field": "power_play_goals",
            "raw_totals_require_schedule_and_availability_context": True,
            "team_games_available_required_for_availability_rate": True,
        },
        "source_availability": {key: value is not None for key, value in raw_payloads.items()},
        "source_provenance": dict(source_provenance or {}),
        "player_season_stats": player_stats,
        "player_season_stats_count": len(player_stats),
        "notes": [
            "Historical evidence is isolated from the active league workspace.",
            "Games played must accompany historical production comparisons.",
            "PPG in fantasy context means Points Per Game, not power-play goals.",
        ],
    }
