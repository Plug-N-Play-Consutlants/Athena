"""Confidence propagation helpers for explainable intelligence."""
from __future__ import annotations

from typing import Iterable

from Intelligence.Explainability import ConfidenceReport, EvidenceBundle, ReasoningTrace, confidence_label

CONFIDENCE_PROPAGATION_VERSION = "0.5.5.1.0"


def propagate_confidence(route_confidence: float = 0.45, evidence: EvidenceBundle | None = None, reasoning: ReasoningTrace | None = None) -> ConfidenceReport:
    evidence = evidence or EvidenceBundle()
    reasoning = reasoning or ReasoningTrace()
    evidence_score = evidence.average_confidence()
    step_bonus = min(0.12, len(reasoning.steps) * 0.02)
    penalty = 0.0
    uncertainty: list[str] = []
    if evidence.source_counts().get("knowledge", 0) == 0:
        penalty += 0.05
        uncertainty.append("No direct knowledge evidence was retrieved by the explainability layer.")
    if evidence.source_counts().get("events", 0) == 0:
        uncertainty.append("No event evidence was attached to this explanation trace.")
    score = (max(0.0, min(1.0, route_confidence)) * 0.45) + (evidence_score * 0.45) + step_bonus - penalty
    score = round(max(0.0, min(0.95, score)), 4)
    factors = (
        f"route_confidence={round(route_confidence, 4)}",
        f"evidence_confidence={evidence_score}",
        f"reasoning_steps={len(reasoning.steps)}",
    )
    return ConfidenceReport(score=score, label=confidence_label(score), factors=factors, uncertainty=tuple(uncertainty))


__all__ = ["CONFIDENCE_PROPAGATION_VERSION", "propagate_confidence"]
