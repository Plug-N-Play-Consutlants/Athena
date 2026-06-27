"""Explainability models for Athena intelligence execution.

This layer keeps explanations deterministic and serializable. It is deliberately
small: downstream Scout/UI code can inspect every answer without depending on a
large AI runtime or provider-specific objects.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Tuple

EXPLAINABLE_INTELLIGENCE_VERSION = "0.5.5.1.0"


@dataclass(frozen=True)
class EvidenceItem:
    source: str
    label: str
    detail: str = ""
    confidence: float = 0.5
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceBundle:
    knowledge: Tuple[EvidenceItem, ...] = ()
    historical: Tuple[EvidenceItem, ...] = ()
    events: Tuple[EvidenceItem, ...] = ()
    identity: Tuple[EvidenceItem, ...] = ()
    provider: Tuple[EvidenceItem, ...] = ()
    rules: Tuple[EvidenceItem, ...] = ()
    external: Tuple[EvidenceItem, ...] = ()

    def all_items(self) -> Tuple[EvidenceItem, ...]:
        return self.knowledge + self.historical + self.events + self.identity + self.provider + self.rules + self.external

    def source_counts(self) -> Dict[str, int]:
        return {
            "knowledge": len(self.knowledge),
            "historical": len(self.historical),
            "events": len(self.events),
            "identity": len(self.identity),
            "provider": len(self.provider),
            "rules": len(self.rules),
            "external": len(self.external),
        }

    def average_confidence(self) -> float:
        items = self.all_items()
        if not items:
            return 0.35
        return round(sum(max(0.0, min(1.0, item.confidence)) for item in items) / len(items), 4)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_counts": self.source_counts(),
            "average_confidence": self.average_confidence(),
            "items": [item.to_dict() for item in self.all_items()],
        }


@dataclass(frozen=True)
class ReasoningStep:
    step_id: str
    label: str
    status: str = "pass"
    detail: str = ""
    confidence_delta: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReasoningTrace:
    steps: Tuple[ReasoningStep, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {"steps": [step.to_dict() for step in self.steps], "step_count": len(self.steps)}


@dataclass(frozen=True)
class ConfidenceReport:
    score: float
    label: str
    factors: Tuple[str, ...] = ()
    uncertainty: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExplainabilityResult:
    question: str
    intent: str
    sport: str = ""
    league: str = ""
    entities: Tuple[str, ...] = ()
    modules: Tuple[str, ...] = ()
    evidence: EvidenceBundle = field(default_factory=EvidenceBundle)
    reasoning: ReasoningTrace = field(default_factory=ReasoningTrace)
    confidence: ConfidenceReport = field(default_factory=lambda: ConfidenceReport(0.35, "low"))
    limitations: Tuple[str, ...] = ()
    recommendations: Tuple[str, ...] = ()
    response_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": EXPLAINABLE_INTELLIGENCE_VERSION,
            "question": self.question,
            "intent": self.intent,
            "sport": self.sport,
            "league": self.league,
            "entities": list(self.entities),
            "modules": list(self.modules),
            "evidence": self.evidence.to_dict(),
            "reasoning": self.reasoning.to_dict(),
            "confidence": self.confidence.to_dict(),
            "limitations": list(self.limitations),
            "recommendations": list(self.recommendations),
            "response_summary": self.response_summary,
        }


def confidence_label(score: float) -> str:
    value = max(0.0, min(1.0, float(score)))
    if value >= 0.8:
        return "high"
    if value >= 0.6:
        return "medium"
    return "low"


__all__ = [
    "EXPLAINABLE_INTELLIGENCE_VERSION",
    "EvidenceItem",
    "EvidenceBundle",
    "ReasoningStep",
    "ReasoningTrace",
    "ConfidenceReport",
    "ExplainabilityResult",
    "confidence_label",
]
