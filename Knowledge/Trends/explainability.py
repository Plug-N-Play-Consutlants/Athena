"""
Athena Sports Intelligence Platform

Epic 4D.2d

Trend explainability builder.
"""

from __future__ import annotations

from dataclasses import dataclass

from Knowledge.Trends.confidence_models import ConfidencePackage
from Knowledge.Trends.models import TrendResult, TrendSeries


@dataclass(frozen=True)
class TrendExplanation:
    summary: str
    evidence: list[str]
    confidence: str
    known_gaps: list[str]
    recommendations: list[str]

    def serialize(self) -> dict:
        return {
            "summary": self.summary,
            "evidence": list(self.evidence),
            "confidence": self.confidence,
            "known_gaps": list(self.known_gaps),
            "recommendations": list(self.recommendations),
        }


class TrendExplanationBuilder:
    @classmethod
    def build(cls, series: TrendSeries, result: TrendResult, confidence: ConfidencePackage) -> TrendExplanation:
        summary = (
            f"{result.metric_key} is classified as {result.direction.value} "
            f"with {result.strength.value} strength."
        )
        evidence = [
            f"{len(series.observations)} observation(s) support this trend.",
            f"Momentum score is {result.momentum_score:.3f}.",
            f"Window type is {result.window.window_type.value if result.window else 'unknown'}.",
        ]
        if result.evidence_event_ids:
            evidence.append(f"{len(result.evidence_event_ids)} temporal evidence event(s) are linked.")
        confidence_text = f"{confidence.confidence_band.value} ({confidence.overall_score:.2f})"
        return TrendExplanation(
            summary=summary,
            evidence=evidence,
            confidence=confidence_text,
            known_gaps=list(confidence.known_gaps),
            recommendations=list(confidence.recommendations),
        )
