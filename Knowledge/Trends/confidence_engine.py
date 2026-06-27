"""
Athena Sports Intelligence Platform

Epic 4D.2d

Trend confidence and explainability engine.
"""

from __future__ import annotations

from dataclasses import dataclass

from Knowledge.Trends.confidence import TrendConfidenceCalculator
from Knowledge.Trends.confidence_models import ConfidencePackage
from Knowledge.Trends.explainability import TrendExplanation, TrendExplanationBuilder
from Knowledge.Trends.models import TrendResult, TrendSeries
from Knowledge.Trends.quality import TrendQualityAnalyzer, TrendQualityReport


CONFIDENCE_ENGINE_VERSION = "4D.2-drop4-confidence-explainability"


@dataclass(frozen=True)
class TrendConfidenceEnginePackage:
    confidence: ConfidencePackage
    explanation: TrendExplanation
    quality: TrendQualityReport

    def serialize(self) -> dict:
        return {
            "confidence_engine_version": CONFIDENCE_ENGINE_VERSION,
            "confidence": self.confidence.serialize(),
            "explanation": self.explanation.serialize(),
            "quality": self.quality.serialize(),
        }


class TrendConfidenceEngine:
    VERSION = CONFIDENCE_ENGINE_VERSION

    @classmethod
    def build(cls, series: TrendSeries, result: TrendResult) -> TrendConfidenceEnginePackage:
        quality = TrendQualityAnalyzer.analyze(series)
        confidence = TrendConfidenceCalculator.calculate(series=series, result=result)
        explanation = TrendExplanationBuilder.build(series=series, result=result, confidence=confidence)
        return TrendConfidenceEnginePackage(
            confidence=confidence,
            explanation=explanation,
            quality=quality,
        )

    @classmethod
    def metadata(cls) -> dict:
        return {
            "confidence_engine_version": cls.VERSION,
            "calculator": TrendConfidenceCalculator.__name__,
            "quality_analyzer": TrendQualityAnalyzer.__name__,
            "explanation_builder": TrendExplanationBuilder.__name__,
        }
