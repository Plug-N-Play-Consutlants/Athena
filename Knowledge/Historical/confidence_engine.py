"""
Athena Sports Intelligence Platform

Epic 4D.3e

Historical Signal Confidence + Explainability Engine
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .confidence import HistoricalConfidencePackage, HistoricalSignalConfidenceCalculator
from .explainability import (
    HISTORICAL_EXPLAINABILITY_VERSION,
    HistoricalSignalExplanationBuilder,
)
from .explainability_models import HistoricalSignalExplanation


HISTORICAL_CONFIDENCE_ENGINE_VERSION = "4D.3e-historical-signal-confidence"


@dataclass(slots=True)
class HistoricalExplainabilityPackage:
    confidence: HistoricalConfidencePackage
    explanation: HistoricalSignalExplanation

    def to_dict(self) -> dict[str, Any]:
        return {
            "historical_confidence_engine_version": HISTORICAL_CONFIDENCE_ENGINE_VERSION,
            "historical_explainability_version": HISTORICAL_EXPLAINABILITY_VERSION,
            "confidence": self.confidence.to_dict(),
            "explanation": self.explanation.to_dict(),
        }


class HistoricalExplainabilityEngine:
    VERSION = HISTORICAL_CONFIDENCE_ENGINE_VERSION

    @classmethod
    def build(cls, signal: dict[str, Any]) -> HistoricalExplainabilityPackage:
        confidence = HistoricalSignalConfidenceCalculator.calculate(signal)
        explanation = HistoricalSignalExplanationBuilder.build(signal, confidence)
        return HistoricalExplainabilityPackage(confidence=confidence, explanation=explanation)

    @classmethod
    def metadata(cls) -> dict[str, str]:
        return {
            "historical_confidence_engine_version": HISTORICAL_CONFIDENCE_ENGINE_VERSION,
            "historical_explainability_version": HISTORICAL_EXPLAINABILITY_VERSION,
            "confidence_calculator": HistoricalSignalConfidenceCalculator.__name__,
            "explanation_builder": HistoricalSignalExplanationBuilder.__name__,
        }
