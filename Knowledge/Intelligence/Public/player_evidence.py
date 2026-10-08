"""Resolve public player card facts from acquired NHL evidence by stable identity.

A same-name match is insufficient: NHL IDs or birth date and team/position
must distinguish players. Cached facts retain their season provenance.
"""
from __future__ import annotations

from datetime import date
from functools import lru_cache
import os
from typing import Any

from Core.json_utils import read_optional_json
from Core.project_paths import OUTPUT_DIR, RAW_DIR


@lru_cache(maxsize=1)
def _records():
    identities = read_optional_json(OUTPUT_DIR / "player_identity_map.json") or []
    landing = read_optional_json(RAW_DIR / "nhl_player_landing.json") or {}
    by_id = {str(row.get("nhl_player_id")): row.get("payload") for row in landing.get("players", []) if isinstance(row, dict)}
    return identities, by_id


def _target_season_id():
    """Return the NHL season that is currently in progress or next to begin.

    The NHL season crosses calendar years. From July onward, the season starts
    in the current calendar year; before July it started in the prior year.
    """
    today = date.today()
    start = today.year if today.month >= 7 else today.year - 1
    return f"{start}{start + 1}"


def _name_from_payload(payload):
    def part(value):
        return value.get("default", "") if isinstance(value, dict) else str(value or "")
    return " ".join((part(payload.get("firstName")), part(payload.get("lastName")))).strip()


def _season_rows(payload):
    """One professional regular-season observation per season, newest first."""
    rows = [row for row in payload.get("seasonTotals", []) if isinstance(row, dict)
            and row.get("leagueAbbrev") == "NHL" and row.get("gameTypeId") == 2
            and isinstance(row.get("season"), int)]
    by_season = {}
    for row in rows:
        season = row["season"]
        # A traded player may have team-specific and combined totals. Prefer
        # the row with the most games instead of counting a season twice.
        if season not in by_season or (row.get("gamesPlayed") or 0) > (by_season[season].get("gamesPlayed") or 0):
            by_season[season] = row
    return [by_season[key] for key in sorted(by_season, reverse=True)]


def _season_label(season):
    value = str(season or "")
    return value[:4] + "-" + value[6:] if len(value) == 8 else value


@lru_cache(maxsize=2)
def _season_index(season_id: str):
    """Fetch official skater identities once, then resolve individual landings."""
    try:
        from Providers.NHL.nhl_client import NHLClient
        data = NHLClient().get_skater_summary(season_id)
        return data.get("data", []) if isinstance(data, dict) else []
    except Exception:
        return []


@lru_cache(maxsize=256)
def _live_record(name: str, team: str, position: str, birth_date: str):
    if os.getenv("ATHENA_NHL_PLAYER_NETWORK", "1").lower() not in {"1", "true", "yes", "on"}:
        return None
    # Current displayed production must come from the active season. Stable
    # multi-season assessment is a separate downstream concern.
    season_id = _target_season_id()
    try:
        from Providers.NHL.nhl_client import NHLClient
    except ImportError:
        return None
    start = int(season_id[:4])
    seasons = [f"{year}{year + 1}" for year in range(start, start - 3, -1)]
    for season in seasons:
        for item in _season_index(season):
            if not isinstance(item, dict):
                continue
            listed = str(item.get("skaterFullName") or item.get("playerName") or "").strip()
            if "," in listed:
                last, first = listed.split(",", 1)
                listed = first.strip() + " " + last.strip()
            if listed.casefold() != name.casefold():
                continue
            if position and item.get("positionCode") and item.get("positionCode") != position:
                continue
            teams = str(item.get("teamAbbrevs") or item.get("teamAbbrev") or "")
            if team and team != "NYI/AHL" and birth_date == "" and team not in teams.split(","):
                continue
            nhl_id = item.get("playerId") or item.get("skaterId")
            if not nhl_id:
                continue
            try:
                payload = NHLClient().get_player_landing(str(nhl_id))
            except Exception:
                continue
            if not isinstance(payload, dict) or birth_date and payload.get("birthDate") != birth_date:
                continue
            return {"nhl_player_id": nhl_id, "nhl_team": payload.get("currentTeamAbbrev"), "resolution_status": "resolved"}, payload
    return None



def _valid_season_observation(row: Any) -> bool:
    return (isinstance(row, dict)
            and isinstance(row.get("gp"), (int, float)) and row.get("gp", 0) > 0
            and isinstance(row.get("points"), (int, float)))


def build_statistical_evidence(*, season_history: list[dict[str, Any]], career: dict[str, Any],
                               target_season: str, source: str = "nhl_player_landing") -> dict[str, Any]:
    """Canonical statistical evidence shared by public-player consumers.

    Provider payloads remain available for provenance, but downstream reasoning
    should consume this normalized contract rather than reinterpret NHL landing
    rows independently.
    """
    seasons = [dict(row) for row in season_history if _valid_season_observation(row)]
    latest = dict(seasons[0]) if seasons else {}
    target_start = 0
    latest_start = 0
    try:
        target_start = int(str(target_season or "")[:4])
    except ValueError:
        pass
    try:
        latest_start = int(str(latest.get("season") or "")[:4])
    except ValueError:
        pass
    stale = bool(target_start and latest_start and latest_start < target_start - 1)
    return {
        "contract": "canonical_player_statistical_evidence",
        "source": source,
        "target_season": target_season,
        "season_series": seasons,
        "latest_observed_season": latest,
        "season_count": len(seasons),
        "career": {
            "games": career.get("gamesPlayed"),
            "points": career.get("points"),
            "goals": career.get("goals"),
        },
        "freshness": {
            "status": "stale" if stale else "current_or_recent" if latest else "unavailable",
            "stale_for_current_rating": stale,
            "latest_season": latest.get("season", ""),
        },
        "comparability": {
            "regular_season_nhl": True,
            "usable_seasons": len(seasons),
        },
    }

def authoritative_statistical_view(evidence: dict[str, Any], *, window_size: int = 3) -> dict[str, Any]:
    """Return the single downstream authority for player statistical state.

    Verified canonical statistical evidence owns season availability, freshness,
    career totals and comparable recent windows. Legacy compatibility fields are
    consulted only when the canonical contract is absent.
    """
    statistical = evidence.get("statistical_evidence") if isinstance(evidence.get("statistical_evidence"), dict) else {}
    canonical = statistical.get("contract") == "canonical_player_statistical_evidence"
    series_source = statistical.get("season_series", []) if canonical else evidence.get("season_history", [])
    series = [dict(row) for row in series_source if _valid_season_observation(row)]
    target = str(statistical.get("target_season") if canonical else evidence.get("target_season") or "")
    try:
        target_start = int(target[:4])
    except ValueError:
        target_start = 0
    if target_start:
        # Current production and stable assessment are different views. Early in
        # a new season, keep the assessment window on completed seasons until a
        # minimally meaningful current sample exists.
        current = next((row for row in series if int(str(row.get("season") or "")[:4]) == target_start), None)
        include_current = bool(current and isinstance(current.get("gp"), (int, float)) and current.get("gp", 0) >= 20)
        eligible = [row for row in series if int(str(row.get("season") or "")[:4]) <= target_start and
                    (include_current or int(str(row.get("season") or "")[:4]) < target_start)]
        recent = eligible[:window_size]
    else:
        recent = series[:window_size]
    career = statistical.get("career", {}) if canonical and isinstance(statistical.get("career"), dict) else {
        "games": evidence.get("career_games"), "points": evidence.get("career_points"), "goals": evidence.get("career_goals")
    }
    freshness = statistical.get("freshness", {}) if canonical and isinstance(statistical.get("freshness"), dict) else {}
    return {
        "authority": "canonical_statistical_evidence" if canonical else "legacy_compatibility",
        "season_series": series,
        "recent_window": recent,
        "career": dict(career),
        "freshness": dict(freshness),
        "target_season": target,
        "source": statistical.get("source") if canonical else evidence.get("source", ""),
    }


def player_evidence(name: str, *, team: str = "", position: str = "", birth_date: str = "") -> dict[str, Any]:
    identities, by_id = _records()
    matches = [row for row in identities if isinstance(row, dict) and
               str(row.get("nhl_player_name") or row.get("canonical_player_name") or "").casefold() == name.casefold() and
               str(row.get("resolution_status") or "").lower() == "resolved"]
    candidates = []
    for row in matches:
        payload = by_id.get(str(row.get("nhl_player_id")))
        if not isinstance(payload, dict):
            continue
        if birth_date and payload.get("birthDate") != birth_date:
            continue
        if team and team not in {"NYI/AHL", str(payload.get("currentTeamAbbrev") or ""), str(row.get("nhl_team") or "")}:
            continue
        if position and position != str(payload.get("position") or row.get("nhl_position") or ""):
            continue
        candidates.append((row, payload))
    # The acquired NHL landing cache can outlive a fantasy identity map. An
    # exact birth-date and position match is sufficient to recover the public
    # identity without making an arbitrary same-name choice.
    if not candidates and birth_date:
        for nhl_id, payload in by_id.items():
            if not isinstance(payload, dict) or _name_from_payload(payload).casefold() != name.casefold():
                continue
            if payload.get("birthDate") != birth_date or position and payload.get("position") != position:
                continue
            candidates.append(({"nhl_player_id": nhl_id, "nhl_team": payload.get("currentTeamAbbrev")}, payload))
    if candidates and str((candidates[0][1].get("featuredStats") or {}).get("season") or "") != _target_season_id():
        live = _live_record(name, team, position, birth_date)
        if live:
            candidates = [live]
    if not candidates:
        live = _live_record(name, team, position, birth_date)
        if live:
            candidates.append(live)
    if len(candidates) != 1:
        return {}
    row, payload = candidates[0]
    featured = payload.get("featuredStats") or {}
    featured_season = featured.get("season")
    regular = (featured.get("regularSeason") or {}) if isinstance(featured, dict) else {}
    featured_stats = regular.get("subSeason") or {}
    career = regular.get("career") or {}
    if not isinstance(featured_stats, dict):
        featured_stats = {}
    if not isinstance(career, dict):
        career = {}
    born = payload.get("birthDate")
    try:
        birth = date.fromisoformat(str(born))
        today = date.today()
        age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
    except ValueError:
        age = None

    # Headline/card production is current-season state. NHL landing featuredStats
    # may legitimately remain on the last completed season early in autumn, so
    # select the active season from seasonTotals instead of relabelling old data.
    target_id = int(_target_season_id())
    nhl_seasons = _season_rows(payload)
    current_row = next((item for item in nhl_seasons if int(item.get("season") or 0) == target_id), None)
    if current_row is not None:
        stats = current_row
        season = current_row.get("season")
    elif str(featured_season or "") == str(target_id):
        stats = featured_stats
        season = featured_season
    else:
        stats = {}
        season = target_id

    gp = stats.get("gamesPlayed")
    points = stats.get("points")
    values = {"goals": stats.get("goals"), "assists": stats.get("assists"), "points": points,
              "+/-": stats.get("plusMinus"), "games_played": gp}
    if isinstance(gp, (int, float)) and gp > 0 and isinstance(points, (int, float)):
        values["ppg"] = round(points / gp, 3)
    values = {k: v for k, v in values.items() if v is not None}
    season_label = _season_label(season)
    season_row = {"season": season_label, "team": payload.get("currentTeamAbbrev") or row.get("nhl_team"),
                  "gp": gp, "g": stats.get("goals"), "a": stats.get("assists"),
                  "pts": points, "ppg": values.get("ppg"),
                  "plus_minus": ("+" + str(stats["plusMinus"]) if isinstance(stats.get("plusMinus"), (int, float)) and stats["plusMinus"] > 0 else stats.get("plusMinus"))}
    season_history = [
        {"season": _season_label(item.get("season")), "gp": item.get("gamesPlayed"),
         "goals": item.get("goals"), "assists": item.get("assists"),
         "points": item.get("points"), "plus_minus": item.get("plusMinus")}
        for item in nhl_seasons
    ]
    awards = []
    for item in payload.get("awards", []) or []:
        if not isinstance(item, dict):
            continue
        trophy = item.get("trophy")
        title = trophy.get("default") if isinstance(trophy, dict) else trophy
        years = item.get("seasons") if isinstance(item.get("seasons"), list) else []
        if title and years:
            awards.append({"trophy": str(title), "count": len(years)})
    target_season = _season_label(_target_season_id())
    statistical_evidence = build_statistical_evidence(
        season_history=season_history, career=career, target_season=target_season, source="nhl_player_landing"
    )
    return {"nhl_id": str(row.get("nhl_player_id")), "birth_date": born,
            "age": age, "jersey_number": payload.get("sweaterNumber"),
            "photo_url": payload.get("headshot") or "", "team": payload.get("currentTeamAbbrev") or row.get("nhl_team"),
            "position": payload.get("position") or row.get("nhl_position"), "season": season_label,
            "target_season": target_season,
            "stats": values, "season_statistics": [season_row] if gp is not None else [],
            "statistical_evidence": statistical_evidence,
            "season_history": statistical_evidence["season_series"],  # compatibility projection
            "awards": awards,
            "career_games": statistical_evidence["career"]["games"],
            "career_points": statistical_evidence["career"]["points"],
            "career_goals": statistical_evidence["career"]["goals"],
            "source": "nhl_player_landing"}


def player_tier(evidence: dict[str, Any]) -> str:
    """Compatibility facade; Athena owns the actual player assessment."""
    from Athena.player_assessment import assess_player
    return assess_player(evidence)["current_tier"]
