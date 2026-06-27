"""Trend Intelligence version metadata."""

TREND_DOMAIN_VERSION = "4D.2-drop1-trend-domain"
TREND_ENGINE_VERSION = "4D.2-drop4-confidence-explainability"
TREND_SCHEMA_VERSION = "trend-schema-v1"
WINDOW_ANALYSIS_VERSION = "4D.2-drop3-window-analysis"
COMPARISON_ENGINE_VERSION = "4D.2-drop3-window-analysis"
MOMENTUM_ENGINE_VERSION = "4D.2-drop3-window-analysis"
CONFIDENCE_ENGINE_VERSION = "4D.2-drop4-confidence-explainability"


def metadata() -> dict:
    return {
        "trend_domain_version": TREND_DOMAIN_VERSION,
        "trend_engine_version": TREND_ENGINE_VERSION,
        "trend_schema_version": TREND_SCHEMA_VERSION,
        "window_analysis_version": WINDOW_ANALYSIS_VERSION,
        "comparison_engine_version": COMPARISON_ENGINE_VERSION,
        "momentum_engine_version": MOMENTUM_ENGINE_VERSION,
        "confidence_engine_version": CONFIDENCE_ENGINE_VERSION,
    }
