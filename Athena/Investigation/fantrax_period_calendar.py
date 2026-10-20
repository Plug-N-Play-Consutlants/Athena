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
    source_key = "scoringPeriods" if isinstance(data.get("scoringPeriods"), list) else "rosterPeriods"
    entries = data.get(source_key)
    if not isinstance(entries, list):
        result["reason"] = "No documented scoring or roster period schedule"
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
        return parse_period_calendar(client.get("https://www.fantrax.com/fxea/general/getLeagueInfo"), period)
    except Exception as exc:
        # Do not leak authenticated URLs or tokens through exception strings.
        return {"status": "unavailable", "reason": f"{type(exc).__name__} fetching documented league calendar"}
