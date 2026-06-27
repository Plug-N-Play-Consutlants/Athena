"""
Athena Sports Intelligence Platform

Epic 4D.3e

Historical Signal Confidence
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HistoricalConfidenceBand(str, Enum):
    INSUFFICIENT = "insufficient"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass(slots=True)
class HistoricalConfidenceComponent:
    name: str
    score: float
    weight: float
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "score": self.score,
            "weight": self.weight,
            "explanation": self.explanation,
        }


@dataclass(slots=True)
class HistoricalConfidencePackage:
    score: float
    band: HistoricalConfidenceBand
    components: list[HistoricalConfidenceComponent] = field(default_factory=list)
    known_gaps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "band": self.band.value,
            "components": [component.to_dict() for component in self.components],
            "known_gaps": self.known_gaps,
        }


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def confidence_band(score: float) -> HistoricalConfidenceBand:
    if score < 0.20:
        return HistoricalConfidenceBand.INSUFFICIENT
    if score < 0.40:
        return HistoricalConfidenceBand.LOW
    if score < 0.70:
        return HistoricalConfidenceBand.MEDIUM
    if score < 0.90:
        return HistoricalConfidenceBand.HIGH
    return HistoricalConfidenceBand.VERY_HIGH


class HistoricalSignalConfidenceCalculator:
    """Builds deterministic confidence for historical trend signals."""

    @classmethod
    def calculate(cls, signal: dict[str, Any]) -> HistoricalConfidencePackage:
        comparison_count = int(signal.get("comparison_count") or 0)
        evidence_count = len(signal.get("evidence_comparison_ids") or [])
        known_gaps = list(signal.get("known_gaps") or [])
        base_confidence = float(signal.get("confidence") or 0.0)
        direction = str(signal.get("direction") or "unknown")

        components = [
            HistoricalConfidenceComponent(
                name="base_signal_confidence",
                score=_clamp(base_confidence),
                weight=0.35,
                explanation=f"Signal confidence is {base_confidence:.4f}.",
            ),
            HistoricalConfidenceComponent(
                name="comparison_coverage",
                score=_clamp(comparison_count / 4.0),
                weight=0.25,
                explanation=f"Signal is supported by {comparison_count} comparison(s).",
            ),
            HistoricalConfidenceComponent(
                name="evidence_linkage",
                score=_clamp(evidence_count / max(1, comparison_count)),
                weight=0.20,
                explanation=f"{evidence_count} evidence comparison id(s) are linked.",
            ),
            HistoricalConfidenceComponent(
                name="direction_clarity",
                score=0.35 if direction == "unknown" else 0.85,
                weight=0.20,
                explanation=f"Historical direction is {direction}.",
            ),
        ]

        weighted = sum(component.score * component.weight for component in components)
        weights = sum(component.weight for component in components)
        score = round(_clamp(weighted / weights if weights else 0.0), 4)

        return HistoricalConfidencePackage(
            score=score,
            band=confidence_band(score),
            components=components,
            known_gaps=known_gaps,
        )
