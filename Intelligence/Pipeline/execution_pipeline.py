"""Canonical explainable intelligence execution pipeline."""
from __future__ import annotations

from typing import Any, Dict

from Intelligence.Confidence import propagate_confidence
from Intelligence.Explainability import (
    EXPLAINABLE_INTELLIGENCE_VERSION,
    EvidenceBundle,
    EvidenceItem,
    ExplainabilityResult,
    ReasoningStep,
    ReasoningTrace,
)

EXPLAINABLE_PIPELINE_VERSION = "0.5.5.1.0"


def _evidence_from_route(route: Any) -> EvidenceBundle:
    route_evidence = tuple(
        EvidenceItem(source="routing", label="Route Evidence", detail=str(item), confidence=0.58)
        for item in getattr(route, "evidence", ())
    )
    identity_evidence = tuple(
        EvidenceItem(source="identity_registry", label="Resolved Entity", detail=str(label), confidence=0.72)
        for label in getattr(route, "entity_labels", ())
    )
    module_evidence = tuple(
        EvidenceItem(source="capability_registry", label="Selected Module", detail=str(module), confidence=0.66)
        for module in getattr(route, "intelligence_modules", ())
    )
    capability_evidence = tuple(
        EvidenceItem(source="capability_source", label="Available Evidence Source", detail=str(source), confidence=0.6)
        for source in getattr(route, "capability_sources", ())
    )
    event_evidence = tuple(
        EvidenceItem(source="event_intelligence", label="Event capability available", detail="event_assessment selected", confidence=0.62)
        for module in getattr(route, "intelligence_modules", ())
        if module == "event_assessment"
    )
    return EvidenceBundle(
        knowledge=module_evidence + capability_evidence,
        events=event_evidence,
        identity=identity_evidence,
        provider=route_evidence,
    )


def _reasoning_from_route(route: Any) -> ReasoningTrace:
    steps = [
        ReasoningStep("intent_detection", "Intent detected", detail=getattr(route, "intent", "general"), confidence_delta=0.03),
        ReasoningStep("sport_detection", "Sport context detected", detail=getattr(route, "sport", "") or "not detected", confidence_delta=0.04 if getattr(route, "sport", "") else -0.02),
        ReasoningStep("entity_resolution", "Entity resolution evaluated", detail=", ".join(getattr(route, "entity_labels", ()) or ()) or "no entity resolved", confidence_delta=0.05 if getattr(route, "entities", ()) else -0.01),
        ReasoningStep("capability_discovery", "Capability registry queried", detail=", ".join(getattr(route, "intelligence_modules", ()) or ()) or "no modules selected", confidence_delta=0.04 if getattr(route, "intelligence_modules", ()) else -0.03),
        ReasoningStep("evidence_aggregation", "Evidence bundle assembled", detail="route, identity, capability, and event evidence normalized", confidence_delta=0.03),
        ReasoningStep("confidence_propagation", "Confidence propagated", detail="route and evidence confidence combined", confidence_delta=0.02),
    ]
    if getattr(route, "ambiguity", False):
        steps.append(ReasoningStep("ambiguity", "Ambiguity detected", status="warn", detail="More than one entity candidate matched.", confidence_delta=-0.08))
    return ReasoningTrace(tuple(steps))


def execute_explainable_intelligence(question: str, mode: str = "public") -> ExplainabilityResult:
    try:
        from Knowledge.Intelligence.Routing.multi_sport_router import route_multi_sport_query as _route_multi_sport_query
    except Exception:  # pragma: no cover
        _route_multi_sport_query = None  # type: ignore
    if _route_multi_sport_query is None:
        route = None
    else:
        route = _route_multi_sport_query(question, mode=mode)
    if route is None:
        evidence = EvidenceBundle(provider=(EvidenceItem(source="pipeline", label="Routing unavailable", detail="multi_sport_router could not be imported", confidence=0.2),))
        reasoning = ReasoningTrace((ReasoningStep("routing", "Routing unavailable", status="fail", detail="Router import failed", confidence_delta=-0.2),))
        confidence = propagate_confidence(0.2, evidence, reasoning)
        return ExplainabilityResult(question=question, intent="unknown", evidence=evidence, reasoning=reasoning, confidence=confidence, limitations=("Routing layer unavailable.",), response_summary="Athena could not route this request.")

    evidence = _evidence_from_route(route)
    reasoning = _reasoning_from_route(route)
    confidence = propagate_confidence(getattr(route, "confidence", 0.45), evidence, reasoning)
    limitations: list[str] = []
    if not getattr(route, "entities", ()):
        limitations.append("No canonical entity was resolved for this request.")
    if not getattr(route, "intelligence_modules", ()):
        limitations.append("No intelligence modules were selected by the capability registry.")
    if getattr(route, "blocked_sources", ()):
        limitations.append("Blocked context sources: " + ", ".join(getattr(route, "blocked_sources", ())))
    recommendations = (
        "Use this trace during Epic 5 acceptance to identify where Scout requests stop producing data.",
        "Attach hydrated knowledge evidence in the integration/stabilization cycle.",
    )
    summary = "Explainable pipeline completed with " + str(len(reasoning.steps)) + " reasoning steps and " + confidence.label + " confidence."
    return ExplainabilityResult(
        question=question,
        intent=getattr(route, "intent", "general"),
        sport=getattr(route, "sport", ""),
        league=getattr(route, "league", ""),
        entities=tuple(getattr(route, "entity_labels", ()) or getattr(route, "entities", ()) or ()),
        modules=tuple(getattr(route, "intelligence_modules", ()) or ()),
        evidence=evidence,
        reasoning=reasoning,
        confidence=confidence,
        limitations=tuple(limitations),
        recommendations=recommendations,
        response_summary=summary,
    )


def studio_explainability_diagnostics() -> Dict[str, Any]:
    samples = (
        "Compare Auston Matthews vs Connor McDavid in the NHL",
        "Summarize Blue Jays injuries",
        "Tell me about the Toronto Raptors",
    )
    traces = [execute_explainable_intelligence(sample).to_dict() for sample in samples]
    return {
        "panel": "explainable_intelligence",
        "version": EXPLAINABLE_PIPELINE_VERSION,
        "status": "pass" if all(trace["reasoning"]["step_count"] >= 5 for trace in traces) else "warn",
        "sample_count": len(traces),
        "traces": traces,
        "supports": ["execution pipeline", "evidence bundle", "reasoning trace", "confidence propagation", "Scout explainability payload"],
    }


__all__ = [
    "EXPLAINABLE_PIPELINE_VERSION",
    "execute_explainable_intelligence",
    "studio_explainability_diagnostics",
]
