"""Validate Fantrax's documented league period schedule (fxea/getLeagueInfo).

Calendar boundaries establish a time window, not a completed scoring result,
lineup eligibility, or player-period statistics. No inferred weekly cadence.
"""
from __future__ import annotations
from datetime import date, datetime, timezone
from typing import Any


def _day(value: Any) -> date | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(value / (1000 if value > 10**11 else 1), timezone.utc).date()
        except (ValueError, OverflowError, OSError):
            return None
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def parse_period_calendar(payload: Any, period: int, *, today: date | None = None) -> dict:
    """Fail closed on absent, conflicting, or malformed provider boundaries."""
    result = {"status": "unverified", "period": period, "start": None, "end": None,
              "completed": False, "source": "fantrax_fxea_getLeagueInfo", "reason": ""}
    if not isinstance(payload, dict) or not isinstance(period, int) or period < 1:
        result["reason"] = "Invalid league-info response or period"
        return result
    data = payload.get("data", payload)
    if not isinstance(data, dict):
        result["reason"] = "Invalid league-info envelope"
        return result
    # Fantrax documents both scoringPeriods and rosterPeriods. They are not
    # interchangeable; prefer scoringPeriods, and identify roster-only evidence.
    source_key = "scoringPeriods"
    entries = data.get(source_key)
    if not isinstance(entries, list):
        result["reason"] = "No documented scoring-period schedule (rosterPeriods are not scoring periods)"
        return result
    matches = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        value = entry.get("period", entry.get("number", entry.get("periodNumber")))
        try:
            number = int(value)
        except (ValueError, TypeError):
            continue
        if number == period:
            start, end = _day(entry.get("startDate")), _day(entry.get("endDate"))
            if start and end and start <= end:
                matches.append((start, end))
    if len(matches) != 1:
        result["reason"] = "Period boundary missing, invalid, or ambiguous"
        return result
    start, end = matches[0]
    result.update(status="verified_boundary", start=start.isoformat(), end=end.isoformat(),
                  source=f"fantrax_fxea_getLeagueInfo.{source_key}",
                  completed=(today or datetime.now(timezone.utc).date()) > end,
                  reason="Calendar end passed" if (today or datetime.now(timezone.utc).date()) > end else "Calendar period not yet ended")
    return result


def acquire_period_calendar(league_id: str | None, season: Any, period: int | None, client_factory=None) -> dict:
    if not league_id or period is None:
        return {"status": "not_attempted", "reason": "League and period required"}
    try:
        if client_factory is None:
            from Providers.Fantrax.fantrax_client import FantraxClient
            client_factory = FantraxClient
        client = client_factory(league_id=league_id, season=season)
        return parse_period_calendar(client.get_league(), period)
    except Exception as exc:
        # Do not leak authenticated URLs or tokens through exception strings.
        return {"status": "unavailable", "reason": f"{type(exc).__name__} fetching documented league calendar"}


def resolve_latest_completed_scoring_period(payload: Any, *, today: date | None = None) -> dict:
    """Find last elapsed *scoring* calendar period, never a roster period.

    Calendar closure does not certify standings finalization.
    """
    data = payload.get("data", payload) if isinstance(payload, dict) else None
    entries = data.get("scoringPeriods") if isinstance(data, dict) else None
    if not isinstance(entries, list) or not entries:
        return {"status": "unverified", "period": None, "reason": "scoringPeriods missing"}
    numbers = []
    for entry in entries:
        if not isinstance(entry, dict):
            return {"status": "unverified", "period": None, "reason": "malformed scoring period"}
        raw = entry.get("period", entry.get("number", entry.get("periodNumber")))
        try:
            number = int(raw)
        except (TypeError, ValueError):
            return {"status": "unverified", "period": None, "reason": "missing period number"}
        numbers.append(number)
    if any(number < 1 for number in numbers) or len(set(numbers)) != len(numbers):
        return {"status": "unverified", "period": None, "reason": "invalid or duplicate scoring periods"}
    closed = []
    windows = []
    for number in numbers:
        parsed = parse_period_calendar(payload, number, today=today)
        if parsed["status"] != "verified_boundary":
            return {"status": "unverified", "period": None, "reason": parsed["reason"]}
        windows.append((number, date.fromisoformat(parsed["start"]), date.fromisoformat(parsed["end"])))
        if parsed["completed"]:
            closed.append(number)
    ordered = sorted(windows)
    if any(ordered[i][1] <= ordered[i-1][2] or ordered[i][1] <= ordered[i-1][1]
           for i in range(1, len(ordered))):
        return {"status": "unverified", "period": None, "reason": "overlapping or nonmonotonic scoring calendar"}
    return {"status": "calendar_closed", "period": max(closed) if closed else None,
            "reason": "Scoring-period calendar elapsed; standings finalization unverified",
            "source": "fantrax_fxea_getLeagueInfo.scoringPeriods"}



def resolve_roster_period_acquisition_candidate(payload: Any, *, today: date | None = None) -> dict:
    """Roster calendar can nominate an elapsed period for evidence acquisition,
    but never certify scoring-period boundaries, standings, or completion."""
    data = payload.get("data", payload) if isinstance(payload, dict) else None
    entries = data.get("rosterPeriods") if isinstance(data, dict) else None
    if not isinstance(entries, list) or not entries:
        return {"status": "unverified", "period": None, "reason": "rosterPeriods missing"}
    elapsed = []
    seen = set()
    current = today or datetime.now(timezone.utc).date()
    for entry in entries:
        if not isinstance(entry, dict):
            return {"status": "unverified", "period": None, "reason": "invalid roster entry"}
        try:
            number = int(entry.get("period", entry.get("number", entry.get("periodNumber"))))
        except (TypeError, ValueError):
            return {"status": "unverified", "period": None, "reason": "missing roster period number"}
        start, end = _day(entry.get("startDate")), _day(entry.get("endDate"))
        if number < 1 or number in seen or not start or not end or start > end:
            return {"status": "unverified", "period": None, "reason": "ambiguous roster calendar"}
        seen.add(number)
        if current > end:
            elapsed.append(number)
    return {"status": "acquisition_candidate", "period": max(elapsed) if elapsed else None,
            "reason": "Elapsed roster period; scoring period and standings not verified",
            "source": "fantrax_fxea_getLeagueInfo.rosterPeriods"}


def acquire_roster_period_acquisition_candidate(league_id, season, client_factory=None, *, today=None):
    if not league_id:
        return {"status": "unverified", "period": None, "reason": "missing league ID"}
    try:
        if client_factory is None:
            from Providers.Fantrax.fantrax_client import FantraxClient
            client_factory = FantraxClient
        return resolve_roster_period_acquisition_candidate(
            client_factory(league_id=league_id, season=season).get_league(), today=today)
    except Exception as exc:
        return {"status": "unavailable", "period": None,
                "reason": type(exc).__name__ + " acquiring roster calendar"}

def acquire_latest_completed_scoring_period(league_id: str | None, season: Any, client_factory=None, *, today=None) -> dict:
    if not league_id:
        return {"status": "unverified", "period": None, "reason": "missing league ID"}
    try:
        if client_factory is None:
            from Providers.Fantrax.fantrax_client import FantraxClient
            client_factory = FantraxClient
        client = client_factory(league_id=league_id, season=season)
        return resolve_latest_completed_scoring_period(client.get_league(), today=today)
    except Exception as exc:
        return {"status": "unavailable", "period": None, "reason": type(exc).__name__ + " acquiring scoring calendar"}


def resolve_unified_period(payload: Any, *, today: date | None = None) -> dict:
    """Resolve one league reporting calendar, retaining provider schedule provenance.

    Scoring and roster period indices are equivalent only when both supplied
    schedules agree. A single valid schedule is sufficient to select an
    acquisition/reporting period, but never certifies finalized results.
    """
    data = payload.get("data", payload) if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return {"status": "unverified", "period": None, "reason": "invalid league response"}
    calendars = {}
    for key in ("scoringPeriods", "rosterPeriods"):
        entries = data.get(key)
        if not isinstance(entries, list) or not entries:
            continue
        parsed = {}
        for row in entries:
            if not isinstance(row, dict):
                return {"status": "unverified", "period": None, "reason": f"invalid {key} entry"}
            try:
                number = int(row.get("period", row.get("number", row.get("periodNumber"))))
            except (TypeError, ValueError):
                return {"status": "unverified", "period": None, "reason": f"invalid {key} number"}
            start, end = _day(row.get("startDate")), _day(row.get("endDate"))
            if number < 1 or number in parsed or start is None or end is None or start > end:
                return {"status": "unverified", "period": None, "reason": f"invalid {key} boundaries"}
            parsed[number] = (start, end)
        ordered = sorted(parsed.items())
        if any(ordered[i][1][0] <= ordered[i-1][1][1] for i in range(1, len(ordered))):
            return {"status": "unverified", "period": None, "reason": f"overlapping {key} boundaries"}
        calendars[key] = parsed
    if not calendars:
        return {"status": "unverified", "period": None, "reason": "no period schedules"}
    if len(calendars) == 2 and calendars["scoringPeriods"] != calendars["rosterPeriods"]:
        return {"status": "calendar_conflict", "period": None, "reason": "scoring and roster schedules differ; explicit mapping required"}
    key = "scoringPeriods" if "scoringPeriods" in calendars else "rosterPeriods"
    schedule = calendars[key]
    current = today or datetime.now(timezone.utc).date()
    closed = [number for number, (_, end) in schedule.items() if end < current]
    selected = max(closed) if closed else None
    start, end = schedule[selected] if selected else (None, None)
    return {"status": "calendar_closed" if selected else "no_completed_period", "period": selected,
            "start": start.isoformat() if start else None, "end": end.isoformat() if end else None,
            "source": "+".join(sorted(calendars)), "reason": "Shared period schedule; results finalization separately verified",
            "schedule": {n: {"start": a.isoformat(), "end": b.isoformat()} for n, (a, b) in schedule.items()}}


def acquire_unified_period(league_id, season, client_factory=None, *, today=None):
    if not league_id:
        return {"status": "unverified", "period": None, "reason": "missing league ID"}
    try:
        if client_factory is None:
            from Providers.Fantrax.fantrax_client import FantraxClient
            client_factory = FantraxClient
        return resolve_unified_period(client_factory(league_id=league_id, season=season).get_league(), today=today)
    except Exception as exc:
        return {"status": "unavailable", "period": None, "reason": type(exc).__name__ + " acquiring period schedule"}
