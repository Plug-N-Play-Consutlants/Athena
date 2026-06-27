"""Epic 4D.2c comparison engine for trend series."""

from __future__ import annotations

from dataclasses import dataclass

from Knowledge.Trends.comparison import WindowComparator, WindowComparison
from Knowledge.Trends.momentum import MomentumAnalyzer, MomentumResult
from Knowledge.Trends.models import TrendSeries
from Knowledge.Trends.windows import TrendWindowBuilder, WindowStatistics
from Knowledge.Trends.version import COMPARISON_ENGINE_VERSION


@dataclass(frozen=True)
class ComparisonPackage:
    windows: dict
    comparisons: dict[str, WindowComparison]
    momentum: MomentumResult

    @property
    def summary(self) -> dict:
        return {
            "window_count": len(self.windows),
            "comparison_count": len(self.comparisons),
            "momentum_score": self.momentum.score,
            "direction": self.momentum.direction.value,
            "accelerating": self.momentum.accelerating,
            "decelerating": self.momentum.decelerating,
        }

    def serialize(self) -> dict:
        return {
            "windows": {key.value: value.to_dict() for key, value in self.windows.items()},
            "comparisons": {key: value.to_dict() for key, value in self.comparisons.items()},
            "momentum": self.momentum.to_dict(),
        }


class ComparisonEngine:
    VERSION = COMPARISON_ENGINE_VERSION

    @classmethod
    def build(cls, series: TrendSeries) -> ComparisonPackage:
        windows = TrendWindowBuilder.build_all(series.observations)
        comparisons = WindowComparator.compare_all(windows)
        momentum = MomentumAnalyzer.build(comparisons.get("short_vs_medium"), comparisons.get("medium_vs_long"))
        return ComparisonPackage(windows=windows, comparisons=comparisons, momentum=momentum)

    @classmethod
    def metadata(cls) -> dict:
        return {
            "comparison_engine_version": cls.VERSION,
            "window_builder_version": TrendWindowBuilder.VERSION,
            "window_comparator_version": WindowComparator.VERSION,
            "momentum_analyzer_version": MomentumAnalyzer.VERSION,
        }
