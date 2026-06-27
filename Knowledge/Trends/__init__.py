"""Canonical Trend Intelligence domain package."""

from Knowledge.Trends.engine import (
    TREND_ENGINE_REPORT_FILE,
    TREND_RESULTS_FILE,
    TREND_SERIES_FILE,
    TREND_SUMMARY_FILE,
    build_trend_intelligence,
    build_trend_series,
    build_trends_from_series,
    calculate_trend_result,
    observations_from_temporal_events,
    trends_for_entity,
)
from Knowledge.Trends.enums import (
    TrendConfidenceBand,
    TrendDirection,
    TrendStrength,
    TrendType,
    TrendValueKind,
    TrendWindowType,
)
from Knowledge.Trends.metadata import trend_metadata
from Knowledge.Trends.models import (
    Trend,
    TrendMetric,
    TrendObservation,
    TrendResult,
    TrendSeries,
    TrendWindow,
    clamp_confidence,
    confidence_band,
    serialize_trends,
)
from Knowledge.Trends.registry import TrendRegistry, canonical_trend_metrics, get_trend_registry
from Knowledge.Trends.version import (
    TREND_DOMAIN_VERSION,
    TREND_ENGINE_VERSION,
    TREND_SCHEMA_VERSION,
    WINDOW_ANALYSIS_VERSION,
    COMPARISON_ENGINE_VERSION,
    MOMENTUM_ENGINE_VERSION,
    CONFIDENCE_ENGINE_VERSION,
)
from Knowledge.Trends.windows import TrendWindowBuilder, WindowStatistics
from Knowledge.Trends.comparison import WindowComparator, WindowComparison
from Knowledge.Trends.momentum import MomentumAnalyzer, MomentumResult
from Knowledge.Trends.comparison_engine import ComparisonEngine, ComparisonPackage
from Knowledge.Trends.confidence_models import (
    ConfidenceBand,
    ConfidenceComponent,
    ConfidenceFactor,
    ConfidencePackage,
)
from Knowledge.Trends.quality import TrendQualityAnalyzer, TrendQualityReport
from Knowledge.Trends.confidence import TrendConfidenceCalculator, confidence_band as trend_confidence_band
from Knowledge.Trends.explainability import TrendExplanation, TrendExplanationBuilder
from Knowledge.Trends.confidence_engine import (
    TrendConfidenceEngine,
    TrendConfidenceEnginePackage,
)

__all__ = [
    "TREND_DOMAIN_VERSION",
    "TREND_ENGINE_VERSION",
    "TREND_ENGINE_REPORT_FILE",
    "TREND_RESULTS_FILE",
    "TREND_SCHEMA_VERSION",
    "TREND_SERIES_FILE",
    "TREND_SUMMARY_FILE",
    "Trend",
    "TrendConfidenceBand",
    "TrendDirection",
    "TrendMetric",
    "TrendObservation",
    "TrendRegistry",
    "TrendResult",
    "TrendSeries",
    "TrendStrength",
    "TrendType",
    "TrendValueKind",
    "TrendWindow",
    "TrendWindowType",
    "build_trend_intelligence",
    "build_trend_series",
    "build_trends_from_series",
    "calculate_trend_result",
    "canonical_trend_metrics",
    "clamp_confidence",
    "confidence_band",
    "get_trend_registry",
    "observations_from_temporal_events",
    "serialize_trends",
    "trend_metadata",
    "trends_for_entity",
    "WINDOW_ANALYSIS_VERSION",
    "COMPARISON_ENGINE_VERSION",
    "MOMENTUM_ENGINE_VERSION",
    "CONFIDENCE_ENGINE_VERSION",
    "TrendWindowBuilder",
    "WindowStatistics",
    "WindowComparator",
    "WindowComparison",
    "MomentumAnalyzer",
    "MomentumResult",
    "ComparisonEngine",
    "ComparisonPackage",
    "ConfidenceBand",
    "ConfidenceComponent",
    "ConfidenceFactor",
    "ConfidencePackage",
    "TrendQualityAnalyzer",
    "TrendQualityReport",
    "TrendConfidenceCalculator",
    "trend_confidence_band",
    "TrendExplanation",
    "TrendExplanationBuilder",
    "TrendConfidenceEngine",
    "TrendConfidenceEnginePackage",
]
