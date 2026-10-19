"""League-specific fantasy scoring/roster timeline, independent of display timezone.

No schedule, rules or completed-period status is inferred. Caller must supply
verified period boundaries and the applicable league policy. The immutable
snapshot separates event recording from competitive ownership and eligibility.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional


def _aware(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timeline timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class PeriodWindow:
    identifier: str
    first_puck_drop: datetime
    lock_offset_minutes: int = 5
    # End is the *verified league effective end*, not the last game's horn.
    effective_end: Optional[datetime] = None

    @property
    def lock_at(self) -> datetime:
        if not self.identifier or self.lock_offset_minutes < 0:
            raise ValueError("Invalid period identifier or lock offset")
        lock = _aware(self.first_puck_drop) - timedelta(minutes=self.lock_offset_minutes)
        if self.effective_end is not None and _aware(self.effective_end) <= lock:
            raise ValueError("Period end must follow lineup lock")
        return lock


@dataclass(frozen=True)
class TradeTiming:
    recorded_at: datetime
    origin_team: str
    destination_team: str
    active_period: PeriodWindow
    next_period: PeriodWindow
    # This policy is JHLPAA-specific; other leagues must supply their own.
    defer_locked_transactions: bool = True

    def resolve(self) -> dict:
        at = _aware(self.recorded_at)
        current_lock = self.active_period.lock_at
        next_lock = self.next_period.lock_at
        if next_lock <= current_lock:
            raise ValueError("Next period must lock after current period")
        if not self.origin_team or not self.destination_team or self.origin_team == self.destination_team:
            raise ValueError("Trade requires distinct known teams")
        if at < current_lock:
            return {"phase": "pre_lock", "scoring_team": self.destination_team,
                    "next_period_team": self.destination_team, "eligible_from": self.active_period.identifier,
                    "recorded_at_utc": at.isoformat()}
        if at < next_lock:
            # Includes the grey zone after the prior effective period ends.
            # The trade is effective for the upcoming period, not retroactively.
            phase = "locked_period" if self.active_period.effective_end is None or at < _aware(self.active_period.effective_end) else "grey_zone"
            return {"phase": phase, "scoring_team": self.origin_team if phase == "locked_period" else None,
                    "next_period_team": self.destination_team, "eligible_from": self.next_period.identifier,
                    "recorded_at_utc": at.isoformat()}
        if self.defer_locked_transactions:
            return {"phase": "next_period_locked", "scoring_team": self.origin_team,
                    "next_period_team": self.origin_team, "eligible_from": None,
                    "recorded_at_utc": at.isoformat(),
                    "reason": "A subsequent verified period boundary is required"}
        return {"phase": "next_period_locked", "scoring_team": None,
                "next_period_team": None, "eligible_from": None,
                "recorded_at_utc": at.isoformat(), "reason": "League policy not established"}


def earliest_lock(period_id: str, scheduled_puck_drops: list[datetime], *, offset_minutes: int = 5) -> PeriodWindow:
    """Resolve lock from *verified eligible games*; never from local midnight."""
    if not scheduled_puck_drops:
        raise ValueError("Cannot resolve lock without verified eligible games")
    first = min(_aware(d) for d in scheduled_puck_drops)
    window = PeriodWindow(period_id, first, offset_minutes)
    _ = window.lock_at
    return window
