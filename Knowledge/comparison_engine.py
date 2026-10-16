"""Compatibility exports for the canonical historical comparison engine."""

from Knowledge.Historical.comparison_engine import (
    HISTORICAL_COMPARISON_SUMMARY_FILE,
    HISTORICAL_COMPARISONS_FILE,
    build_historical_comparisons,
    comparisons_for_entity,
)

__all__ = [
    "HISTORICAL_COMPARISON_SUMMARY_FILE",
    "HISTORICAL_COMPARISONS_FILE",
    "build_historical_comparisons",
    "comparisons_for_entity",
]