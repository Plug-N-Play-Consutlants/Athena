"""Epic 4D.2c window analysis for Athena Trend Intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import mean
from typing import Iterable, List, Optional, Sequence

from Knowledge.Trends.enums import TrendWindowType
from Knowledge.Trends.models import TrendObservation


def _parse_datetime(value: object) -> datetime:
    if not value:
        return datetime.max.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return datetime.max.replace(tzinfo=timezone.utc)


def _safe_float(value: object) -> Optional[float]:
    if value in (None, "", [], {}):
        return None
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class WindowStatistics:
    window: TrendWindowType
    observation_count: int
    usable_count: int
    minimum: Optional[float]
    maximum: Optional[float]
    average: Optional[float]
    first_value: Optional[float]
    last_value: Optional[float]
    delta: Optional[float]
    start_at: Optional[str]
    end_at: Optional[str]

    def to_dict(self) -> dict:
        return {
            "window": self.window.value,
            "observation_count": self.observation_count,
            "usable_count": self.usable_count,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "average": self.average,
            "first_value": self.first_value,
            "last_value": self.last_value,
            "delta": self.delta,
            "start_at": self.start_at,
            "end_at": self.end_at,
        }


class TrendWindowBuilder:
    """Build deterministic observation-count windows from TrendObservation lists."""

    VERSION = "4D.2-drop3-window-analysis"
    DEFAULT_WINDOWS = {
        TrendWindowType.SHORT: 5,
        TrendWindowType.MEDIUM: 15,
        TrendWindowType.LONG: 30,
        TrendWindowType.ALL_TIME: None,
    }

    @classmethod
    def sort(cls, observations: Iterable[TrendObservation]) -> List[TrendObservation]:
        return sorted(observations, key=lambda obs: (_parse_datetime(obs.observed_at), obs.id))

    @classmethod
    def slice(cls, observations: Sequence[TrendObservation], window: TrendWindowType) -> List[TrendObservation]:
        ordered = cls.sort(observations)
        limit = cls.DEFAULT_WINDOWS.get(window)
        if limit is None:
            return ordered
        return ordered[-limit:]

    @classmethod
    def build(cls, observations: Sequence[TrendObservation], window: TrendWindowType) -> WindowStatistics:
        selected = cls.slice(observations, window)
        numeric = [_safe_float(obs.value) for obs in selected]
        values = [value for value in numeric if value is not None]
        first_value = values[0] if values else None
        last_value = values[-1] if values else None
        delta = None if first_value is None or last_value is None else round(last_value - first_value, 4)
        return WindowStatistics(
            window=window,
            observation_count=len(selected),
            usable_count=len(values),
            minimum=min(values) if values else None,
            maximum=max(values) if values else None,
            average=round(mean(values), 4) if values else None,
            first_value=first_value,
            last_value=last_value,
            delta=delta,
            start_at=selected[0].observed_at if selected else None,
            end_at=selected[-1].observed_at if selected else None,
        )

    @classmethod
    def build_all(cls, observations: Sequence[TrendObservation]) -> dict[TrendWindowType, WindowStatistics]:
        return {window: cls.build(observations, window) for window in cls.DEFAULT_WINDOWS}
