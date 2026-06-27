"""Live Event Reasoning Engine.

This engine consumes canonical EventRecord objects and evidence-fusion output to
produce deterministic, evidence-backed impact assessments. It does not fetch data
and does not mutate Knowledge; it is the reusable algorithmic layer consumed by
Reasoning/Intelligence/Scout.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from Knowledge.Events.evidence_fusion import FusedEvidenceRecord, FusionResult
from Knowledge.Events.models import EventRecord
from Engine.EventReasoning.impact import build_impact_assessment
from Engine.EventReasoning.models import EventReasoningBatch, EventReasoningResult

EVENT_REASONING_ENGINE_VERSION = "0.5.2.1.1"


@dataclass(frozen=True)
class EventImpactCompatibilityAssessment:
    event_id: str
    event_type: str
    subject: str
    impact_category: str
    immediate_impact: str
    short_term_outlook: str
    long_term_outlook: str
    confidence: float
    supporting_evidence: List[str] = field(default_factory=list)
    contradictory_evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)



def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}:" + hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def _confidence_from_event(event: EventRecord) -> float:
    if event.confidence:
        return max(0.0, min(1.0, float(event.confidence)))
    if event.evidence:
        return max(0.0, min(1.0, sum(float(item.confidence) for item in event.evidence) / len(event.evidence)))
    return 0.55


def _summary_for(event: EventRecord, confidence: float, significance: str) -> str:
    subject = event.subject or "This event"
    etype = (event.event_type or "event").replace("_", " ")
    return f"{subject} is a {significance}-significance {etype} event with {confidence:.0%} reasoning confidence."


class EventReasoningEngine:
    """Produce deterministic reasoning for canonical events."""

    version = EVENT_REASONING_ENGINE_VERSION

    def assess(self, event: EventRecord) -> EventImpactCompatibilityAssessment:
        """Compatibility assessment API retained for Engine.Events callers."""
        result = self.reason_about_event(event)
        category_by_type = {
            "injury": "availability",
            "suspension": "availability",
            "trade": "asset_movement",
            "free_agent_signing": "roster_commitment",
            "signing": "roster_commitment",
            "waiver": "roster_churn",
            "claim": "roster_churn",
            "call_up": "opportunity",
            "send_down": "opportunity",
            "schedule_change": "schedule",
            "game_result": "performance_context",
        }
        domains = list(result.impact.affected_domains or [])
        impact_category = category_by_type.get(event.event_type, domains[0] if domains else "context")
        return EventImpactCompatibilityAssessment(
            event_id=result.event_id,
            event_type=result.event_type,
            subject=result.subject,
            impact_category=impact_category,
            immediate_impact=result.impact.immediate,
            short_term_outlook=result.impact.short_term,
            long_term_outlook=result.impact.long_term,
            confidence=result.confidence,
            supporting_evidence=list(result.supporting_evidence),
            contradictory_evidence=list(result.conflicting_evidence),
        )

    def assess_many(self, events: Iterable[EventRecord]) -> List[EventImpactCompatibilityAssessment]:
        return [self.assess(event) for event in events]

    def reason_about_event(self, event: EventRecord, fused_record: Optional[FusedEvidenceRecord] = None) -> EventReasoningResult:
        confidence = float(fused_record.confidence) if fused_record is not None else _confidence_from_event(event)
        confidence = max(0.0, min(1.0, round(confidence, 4)))
        impact = build_impact_assessment(event, confidence)
        supporting = [item.title for item in event.evidence]
        conflicting: List[str] = []
        source_ids = list(getattr(event, "source_ids", []) or [])
        if fused_record is not None:
            supporting = [item.title for item in fused_record.supporting_evidence] or supporting
            conflicting = [item.title for item in fused_record.conflicting_evidence]
            source_ids = list(fused_record.source_ids) or source_ids
        trace = [
            "Loaded canonical EventRecord from Knowledge.Events.",
            "Calculated event confidence from fused evidence when available, otherwise event evidence.",
            f"Classified significance as {impact.significance}.",
            "Generated immediate, short-term, and long-term impact assessment.",
        ]
        return EventReasoningResult(
            reasoning_id=_stable_id("event_reasoning", event.event_id + "|" + event.event_type),
            event_id=event.event_id,
            event_type=event.event_type,
            subject=event.subject,
            executive_summary=_summary_for(event, confidence, impact.significance),
            impact=impact,
            confidence=confidence,
            supporting_evidence=supporting,
            conflicting_evidence=conflicting,
            reasoning_trace=trace,
            source_ids=source_ids,
            timeline_hint=event.occurred_at,
        )

    def reason_about_events(self, events: Iterable[EventRecord], fusion_result: Optional[FusionResult] = None) -> EventReasoningBatch:
        fused_by_event_id: dict[str, FusedEvidenceRecord] = {}
        if fusion_result is not None:
            for fused in fusion_result.fused_records:
                for event_id in fused.event_ids:
                    fused_by_event_id[event_id] = fused
        results = [self.reason_about_event(event, fused_by_event_id.get(event.event_id)) for event in events]
        warnings: List[str] = []
        if not results:
            warnings.append("No events were supplied for live event reasoning.")
        return EventReasoningBatch(version=self.version, results=results, warnings=warnings)


def reason_about_events(events: Iterable[EventRecord], fusion_result: Optional[FusionResult] = None) -> EventReasoningBatch:
    return EventReasoningEngine().reason_about_events(events, fusion_result)
