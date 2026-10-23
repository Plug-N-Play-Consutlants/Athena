"""Acquire verified NHL goals/assists for the league reporting window.

NHL game performances are *not* Fantrax credited points: fantasy period
eligibility, locked lineups, and historical ownership require their own proof.
Fetch game-granular skater summary and boundary-day schedule, not 280+ player
requests. Fail closed if date/window/source coverage cannot be established.
"""
from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from pathlib import Path
import json
import hashlib
import re
from typing import Any

from Core.project_paths import OUTPUT_DIR


def _instant(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        stamp = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        return stamp.astimezone(timezone.utc) if stamp.tzinfo else None
    except ValueError:
        return None


def _season_id(season: Any) -> str | None:
    value = str(season).strip()
    match = re.fullmatch(r"(20\d{2})", value)
    if match:
        year = int(match[1])
        return f"{year}{year + 1}"
    match = re.fullmatch(r"(20\d{2})[-/](\d{2}|20\d{2})", value)
    if match:
        start, suffix = int(match[1]), int(match[2])
        if suffix in (start + 1, (start + 1) % 100):
            return f"{start}{start + 1}"
    return None


def _schedule_starts(payload: Any) -> dict[int, datetime]:
    """Official NHL weekly schedule: gameWeek[] contains startTimeUTC."""
    if not isinstance(payload, dict) or not isinstance(payload.get("gameWeek"), list):
        raise ValueError("NHL schedule has no gameWeek")
    seen: dict[int, datetime] = {}
    for day in payload["gameWeek"]:
        if not isinstance(day, dict) or not isinstance(day.get("games"), list):
            raise ValueError("Invalid NHL schedule day")
        for game in day["games"]:
            if not isinstance(game, dict) or type(game.get("id")) is not int:
                raise ValueError("Invalid NHL schedule game identity")
            timestamp = _instant(game.get("startTimeUTC"))
            if timestamp is None:
                raise ValueError("Invalid NHL game startTimeUTC")
            previous = seen.get(game["id"])
            if previous is not None and previous != timestamp:
                raise ValueError("NHL schedule contains conflicting puck drops")
            seen[game["id"]] = timestamp
    return seen


def normalize_nhl_period_production(payload: Any, schedules: list[Any], *,
                                    league_id: str, season: Any, period: int,
                                    start_at: str, end_at: str,
                                    identity_rows: list, roster_rows: list) -> dict:
    """Validate complete game-granular source and aggregate named rostered skaters.

    No roster eligibility is inferred from the current owner; team attribution
    here is explicitly *current snapshot only*.
    """
    start, end = _instant(start_at), _instant(end_at)
    if start is None or end is None or start >= end or not _season_id(season):
        raise ValueError("Verified offset-aware reporting boundaries and season required")
    if type(period) is not int or period < 1 or not re.fullmatch(r"[A-Za-z0-9]+", str(league_id)):
        raise ValueError("Invalid league or reporting period")
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ValueError("NHL game summary data missing")
    rows = payload["data"]
    if not rows or (type(payload.get("total")) is int and payload["total"] != len(rows)):
        raise ValueError("NHL game result is empty or paginated/incomplete")
    # Exact game start time is needed for boundary-day inclusions/exclusions.
    starts = {}
    for schedule in schedules:
        for game_id, timestamp in _schedule_starts(schedule).items():
            if game_id in starts and starts[game_id] != timestamp:
                raise ValueError("Conflicting NHL schedule responses")
            starts[game_id] = timestamp
    matching: dict[str, dict] = {}
    for row in identity_rows:
        if not isinstance(row, dict) or row.get("resolution_status") != "resolved":
            continue
        if not isinstance(row.get("nhl_player_id"), (str, int)):
            continue
        nhl_id = str(row["nhl_player_id"])
        fantrax_id = str(row.get("fantrax_player_id") or "")
        if nhl_id and fantrax_id:
            if nhl_id in matching and matching[nhl_id]["fantrax_player_id"] != fantrax_id:
                raise ValueError("Conflicting NHL identity assignments")
            matching[nhl_id] = {"fantrax_player_id": fantrax_id, "name": row.get("canonical_player_name") or row.get("fantrax_player_name") or ""}
    roster = {str(row["player_id"]): row for row in roster_rows
              if isinstance(row, dict) and row.get("player_id") is not None}
    crosswalk_rostered = sum(1 for row in matching.values()
                            if row["fantrax_player_id"] in roster)
    observed_games = set()
    totals: dict[str, dict] = {}
    interior_date_start, interior_date_end = start.date(), end.date()
    included_game_ids = set()
    for row in rows:
        if not isinstance(row, dict) or type(row.get("gameId")) is not int:
            raise ValueError("NHL summary requires gameId per record")
        game_id = row["gameId"]
        player_id = row.get("playerId")
        if isinstance(player_id, bool) or not isinstance(player_id, (str, int)) or not str(player_id).isdigit():
            raise ValueError("NHL summary requires playerId per record")
        key = (str(player_id), game_id)
        if key in observed_games:
            raise ValueError("Duplicate NHL player/game evidence")
        observed_games.add(key)
        try:
            game_day = date.fromisoformat(str(row["gameDate"])[:10])
        except (ValueError, KeyError, TypeError):
            raise ValueError("NHL summary requires gameDate") from None
        if not (interior_date_start <= game_day <= interior_date_end):
            raise ValueError("NHL response contains games outside requested date range")
        for field in ("goals", "assists"):
            if type(row.get(field)) is not int or row[field] < 0:
                raise ValueError("Invalid NHL goals or assists")
        if "points" in row and (type(row["points"]) is not int or row["points"] != row["goals"] + row["assists"]):
            raise ValueError("NHL points do not reconcile to goals + assists")
        # Boundary dates can contain NHL games belonging to adjacent reporting
        # periods. Verify actual UTC starts rather than guess by calendar day.
        if game_day in (interior_date_start, interior_date_end):
            if game_id not in starts:
                raise ValueError("Boundary-day game lacks verified NHL puck drop")
            game_start = starts[game_id]
            if game_start.date() < game_day - timedelta(days=1) or game_start.date() > game_day + timedelta(days=1):
                raise ValueError("NHL gameDate disagrees with scheduled start")
            in_scope = start <= game_start <= end
        else:
            in_scope = True
        if not in_scope:
            continue
        included_game_ids.add(game_id)
        linked = matching.get(str(player_id))
        if linked is None or linked["fantrax_player_id"] not in roster:
            continue
        player_key = linked["fantrax_player_id"]
        item = totals.setdefault(player_key, {
            "fantrax_player_id": player_key, "nhl_player_id": str(player_id),
            "player_name": linked["name"] or roster[player_key].get("player_name") or "Unknown",
            "current_owner": roster[player_key].get("owner_team") or None,
            "owner_attribution": ("historical_period_roster_not_confirmed_fantasy_credit" if roster[player_key].get("owner_team_id") else "current_roster_snapshot_only_not_period_eligibility"),
            "goals": 0, "assists": 0, "games_played": 0,
        })
        item["goals"] += row["goals"]
        item["assists"] += row["assists"]
        item["games_played"] += 1
    result_rows = sorted(totals.values(), key=lambda x: (-(x["goals"] + x["assists"]), -x["goals"], x["player_name"]))
    for row in result_rows:
        row["points"] = row["goals"] + row["assists"]
    return {
        "roster_crosswalk_ids": sorted(row["fantrax_player_id"] for row in matching.values()
                                       if row["fantrax_player_id"] in roster),
        "schema": "athena.nhl_window_production.v1", "status": "verified_nhl_window",
        "verified": True, "league_id": str(league_id), "season": str(season),
        "season_id": _season_id(season), "period": period,
        "start_at": start.isoformat(), "end_at": end.isoformat(),
        "source": "nhl_stats_game_summary_plus_nhl_schedule",
        "interpretation": "NHL G+A in reporting window; credited Fantrax points require active lineup and standings reconciliation",
        "game_count": len(included_game_ids), "nhl_game_rows": len(rows),
        "matched_players": len(result_rows),
        "roster_count": len(roster),
        "roster_crosswalk_resolved": crosswalk_rostered,
        "crosswalk_complete": crosswalk_rostered == len(roster),
        "records": result_rows,
    }


def acquire_nhl_period_production(*, league_id: str | None, season: Any, period: int | None,
                                  boundary: dict, client_factory=None, output_dir: Path | None = None,
                                  clock=None, period_rosters: dict | None = None) -> dict:
    """One NHL game-stat call + boundary schedules; cache verified closed windows.

    On errors return bounded status; don't report guessed or partial leaders.
    """
    result = {"status": "not_attempted", "verified": False, "records": [], "reason": ""}
    if not league_id or period is None or not isinstance(boundary, dict):
        result["reason"] = "League, period and reporting window required"
        return result
    start, end = _instant(boundary.get("start_at")), _instant(boundary.get("end_at"))
    if not start or not end or boundary.get("status") != "verified_boundary":
        result["reason"] = "Precise authenticated period boundaries unavailable"
        return result
    if boundary.get("boundary_kind") not in ("points_based_roster_period", "scoring"):
        result["reason"] = "Points-based reporting or scoring-period semantics are not established"
        return result
    now = clock or datetime.now(timezone.utc)
    if now.tzinfo is None:
        result["reason"] = "UTC-aware clock required"
        return result
    if now <= end:
        result["reason"] = "Reporting period has not ended"
        return result
    season_id = _season_id(season)
    if season_id is None:
        result["reason"] = "Unsupported NHL season"
        return result
    # Cache identity must include historical period membership. Otherwise a
    # current-roster-only result from v53 could contaminate a v54 period audit.
    period_rows = (period_rosters or {}).get("records") if isinstance(period_rosters, dict) and period_rosters.get("verified") and period_rosters.get("period") == period else None
    if period_rows is not None:
        normalized_scope = sorted((str(row.get("player_id")), str(row.get("owner_team_id")),
                                   str(row.get("roster_status"))) for row in period_rows)
        scope = "historical_period:" + hashlib.sha256(json.dumps(normalized_scope).encode()).hexdigest()
    else:
        scope = "current_roster_snapshot"
    target_dir = Path(output_dir) if output_dir is not None else OUTPUT_DIR
    identity_path = target_dir / "player_identity_map.json"
    try:
        identity_rows_for_scope = json.loads(identity_path.read_text(encoding="utf-8"))
        if not isinstance(identity_rows_for_scope, list) or not identity_rows_for_scope:
            raise ValueError("Canonical player identity map is missing")
        identity_links = sorted((str(row.get("fantrax_player_id") or ""), str(row.get("nhl_player_id") or ""))
                                for row in identity_rows_for_scope
                                if isinstance(row, dict) and row.get("resolution_status") == "resolved")
        identity_scope = hashlib.sha256(json.dumps(identity_links).encode()).hexdigest()
    except (OSError, ValueError, TypeError) as exc:
        return {**result, "status": "source_unverified", "reason": f"Cannot verify current player identities: {type(exc).__name__}"}
    path = target_dir / "PeriodPlayerProduction" / str(league_id) / str(season) / f"period_{period:03d}.json"
    try:
        if path.is_file():
            cached = json.loads(path.read_text(encoding="utf-8"))
            fetched = _instant(cached.get("fetched_at"))
            if (cached.get("schema") == "athena.nhl_window_production.v1" and
                    cached.get("verified") is True and
                    cached.get("league_id") == str(league_id) and
                    cached.get("season") == str(season) and
                    cached.get("period") == period and
                    cached.get("roster_scope") == scope and
                    cached.get("identity_scope") == identity_scope and
                    cached.get("start_at") == start.isoformat() and
                    cached.get("end_at") == end.isoformat() and
                    fetched and now - fetched < timedelta(hours=12) and
                    isinstance(cached.get("records"), list)):
                return {**cached, "status": "verified_nhl_window", "cached": True}
    except (OSError, ValueError, TypeError):
        pass
    try:
        master_path = target_dir / "player_master.json"
        # Fixture and production both use canonical Output/player_identity_map.
        identity = json.loads(identity_path.read_text(encoding="utf-8"))
        roster = period_rows if period_rows is not None else json.loads(master_path.read_text(encoding="utf-8"))
        if not isinstance(identity, list) or not isinstance(roster, list) or not identity or not roster:
            raise ValueError("Canonical player identity or roster artifact unavailable")
        if client_factory is None:
            from Providers.NHL.nhl_client import NHLClient
            client_factory = NHLClient
        client = client_factory()
        start_date, end_date = start.date(), end.date()
        cayenne = (f'gameDate>="{start_date.isoformat()}" and '
                   f'gameDate<="{end_date.isoformat()} 23:59:59" and '
                   f'gameTypeId=2 and seasonId={season_id}')
        payload = client.get_stats("skater/summary", params={
            "isAggregate": "false", "isGame": "true", "start": 0,
            "limit": -1, "factCayenneExp": "gamesPlayed>=1", "cayenneExp": cayenne,
        })
        boundary_schedules = [client.get_web(f"schedule/{day.isoformat()}")
                              for day in sorted({start_date, end_date})]
        data = normalize_nhl_period_production(payload, boundary_schedules,
            league_id=league_id, season=season, period=period,
            start_at=start.isoformat(), end_at=end.isoformat(),
            identity_rows=identity, roster_rows=roster)
        data["roster_scope"] = scope
        data["identity_scope"] = identity_scope
        data["roster_basis"] = "verified_historical_period" if period_rows is not None else "current_snapshot_only"
        data["fetched_at"] = now.isoformat()
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(path)
        return data
    except (OSError, ValueError, TypeError, KeyError, ImportError) as exc:
        return {**result, "status": "source_unverified", "reason": str(exc)[:180]}
    except Exception as exc:
        # Requests exceptions may contain private URLs; do not dump full message.
        return {**result, "status": "source_unavailable", "reason": f"{type(exc).__name__} acquiring NHL window evidence"}
