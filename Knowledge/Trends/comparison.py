"""Epic 4D.2c window comparison utilities."""

from __future__ import annotations

from dataclasses import dataclass

from Knowledge.Trends.enums import TrendDirection, TrendStrength, TrendWindowType
from Knowledge.Trends.windows import WindowStatistics


@dataclass(frozen=True)
class WindowComparison:
    baseline: str
    comparison: str
    delta: float
    percent_change: float | None
    direction: TrendDirection
    strength: TrendStrength

    def to_dict(self) -> dict:
        return {
            "baseline": self.baseline,
            "comparison": self.comparison,
            "delta": self.delta,
            "percent_change": self.percent_change,
            "direction": self.direction.value,
            "strength": self.strength.value,
        }


class WindowComparator:
    VERSION = "4D.2-drop3-window-analysis"
    STRONG = 0.25
    MODERATE = 0.10
    WEAK = 0.02

    @classmethod
    def _strength(cls, magnitude: float) -> TrendStrength:
        if magnitude >= cls.STRONG:
            return TrendStrength.STRONG
        if magnitude >= cls.MODERATE:
            return TrendStrength.MODERATE
        if magnitude >= cls.WEAK:
            return TrendStrength.WEAK
        return TrendStrength.NONE

    @classmethod
    def compare(cls, previous: WindowStatistics, current: WindowStatistics) -> WindowComparison:
        if previous.average is None or current.average is None:
            return WindowComparison(previous.window.value, current.window.value, 0.0, None, TrendDirection.INSUFFICIENT_DATA, TrendStrength.NONE)
        delta = round(current.average - previous.average, 4)
        percent = None if previous.average == 0 else round(delta / abs(previous.average), 4)
        magnitude = abs(percent) if percent is not None else 0.0
        strength = cls._strength(magnitude)
        if percent is None:
            direction = TrendDirection.STABLE
        elif percent > cls.WEAK:
            direction = TrendDirection.RISING
        elif percent < -cls.WEAK:
            direction = TrendDirection.DECLINING
        else:
            direction = TrendDirection.STABLE
        return WindowComparison(previous.window.value, current.window.value, delta, percent, direction, strength)

    @classmethod
    def compare_all(cls, windows: dict[TrendWindowType, WindowStatistics]) -> dict[str, WindowComparison]:
        comparisons: dict[str, WindowComparison] = {}
        if TrendWindowType.SHORT in windows and TrendWindowType.MEDIUM in windows:
            comparisons["short_vs_medium"] = cls.compare(windows[TrendWindowType.MEDIUM], windows[TrendWindowType.SHORT])
        if TrendWindowType.MEDIUM in windows and TrendWindowType.LONG in windows:
            comparisons["medium_vs_long"] = cls.compare(windows[TrendWindowType.LONG], windows[TrendWindowType.MEDIUM])
        if TrendWindowType.SHORT in windows and TrendWindowType.LONG in windows:
            comparisons["short_vs_long"] = cls.compare(windows[TrendWindowType.LONG], windows[TrendWindowType.SHORT])
        return comparisons
