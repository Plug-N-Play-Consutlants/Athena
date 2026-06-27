"""
Athena Sports Intelligence Platform

Epic 4D.2d

Canonical confidence models for Trend Intelligence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ConfidenceFactor(str, Enum):
    OBSERVATION_COUNT = "observation_count"
    DATA_COMPLETENESS = "data_completeness"
    DATA_FRESHNESS = "data_freshness"
    WINDOW_COVERAGE = "window_coverage"
    METRIC_QUALITY = "metric_quality"
    TREND_STABILITY = "trend_stability"


class ConfidenceBand(str, Enum):
    INSUFFICIENT = "insufficient"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass(frozen=True)
class ConfidenceComponent:
    factor: ConfidenceFactor
    score: float
    weight: float
    explanation: str

    def to_dict(self) -> dict:
        return {
            "factor": self.factor.value,
            "score": self.score,
            "weight": self.weight,
            "explanation": self.explanation,
        }


@dataclass(frozen=True)
class ConfidencePackage:
    overall_score: float
    confidence_band: ConfidenceBand
    components: list[ConfidenceComponent] = field(default_factory=list)
    known_gaps: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def serialize(self) -> dict:
        return {
            "overall_score": self.overall_score,
            "confidence_band": self.confidence_band.value,
            "components": [component.to_dict() for component in self.components],
            "known_gaps": list(self.known_gaps),
            "recommendations": list(self.recommendations),
        }
