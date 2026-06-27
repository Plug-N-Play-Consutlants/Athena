"""Epic 4D.2c momentum analysis."""

from __future__ import annotations

from dataclasses import dataclass

from Knowledge.Trends.comparison import WindowComparison
from Knowledge.Trends.enums import TrendDirection


@dataclass(frozen=True)
class MomentumResult:
    score: float
    direction: TrendDirection
    accelerating: bool
    decelerating: bool
    explanation: str

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "direction": self.direction.value,
            "accelerating": self.accelerating,
            "decelerating": self.decelerating,
            "explanation": self.explanation,
        }


class MomentumAnalyzer:
    VERSION = "4D.2-drop3-window-analysis"

    @staticmethod
    def _clamp(value: float) -> float:
        return round(max(-1.0, min(1.0, value)), 4)

    @classmethod
    def build(cls, short_vs_medium: WindowComparison | None, medium_vs_long: WindowComparison | None = None) -> MomentumResult:
        if short_vs_medium is None:
            return MomentumResult(0.0, TrendDirection.INSUFFICIENT_DATA, False, False, "Insufficient comparison windows.")
        short_signal = short_vs_medium.percent_change or 0.0
        medium_signal = medium_vs_long.percent_change if medium_vs_long and medium_vs_long.percent_change is not None else 0.0
        score = cls._clamp((short_signal * 0.70) + (medium_signal * 0.30))
        accelerating = abs(short_signal) > abs(medium_signal) and abs(short_signal) >= 0.02
        decelerating = abs(short_signal) < abs(medium_signal) and abs(medium_signal) >= 0.02
        if score > 0.02:
            direction = TrendDirection.RISING
        elif score < -0.02:
            direction = TrendDirection.DECLINING
        else:
            direction = TrendDirection.STABLE
        return MomentumResult(
            score=score,
            direction=direction,
            accelerating=accelerating,
            decelerating=decelerating,
            explanation=f"Momentum={score:.4f}; short_vs_medium={short_signal:.4f}; medium_vs_long={medium_signal:.4f}.",
        )
