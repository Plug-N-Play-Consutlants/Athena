"""Deterministic live-event reasoning engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List

from Knowledge.Events.models import EventRecord


IMPACT_BY_TYPE = {
    "injury": ("availability", "Player availability and lineup depth are affected."),
    "trade": ("asset_movement", "Roster construction and team direction are affected."),
    "free_agent_signing": ("roster_commitment", "Organization has committed roster or contract resources."),
    "signing": ("roster_commitment", "Organization has committed roster or contract resources."),
    "waiver": ("roster_churn", "Roster flexibility and replacement value are affected."),
    "claim": ("roster_churn", "Roster flexibility and replacement value are affected."),
    "call_up": ("opportunity", "Player opportunity and team depth chart are affected."),
    "send_down": ("opportunity", "Player opportunity and team depth chart are affected."),
    "demotion": ("opportunity", "Player opportunity and team depth chart are affected."),
    "suspension": ("availability", "Player/team availability is affected by disciplinary status."),
    "schedule_change": ("schedule", "Planning, rest and matchup context are affected."),
    "game_result": ("performance_context", "Recent performance context changed."),
}


@dataclass(frozen=True)
class EventImpactAssessment:
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


class EventReasoningEngine:
    """Turns canonical events into structured impact assessments."""

    def assess(self, event: EventRecord) -> EventImpactAssessment:
        category, template = IMPACT_BY_TYPE.get(event.event_type, ("context", "Event context has changed."))
        confidence = max(0.35, min(0.98, event.confidence or 0.65))
        evidence_titles = [evidence.title for evidence in event.evidence]
        return EventImpactAssessment(
            event_id=event.event_id,
            event_type=event.event_type,
            subject=event.subject,
            impact_category=category,
            immediate_impact=template,
            short_term_outlook=f"Monitor {event.subject} for near-term role, availability or usage changes.",
            long_term_outlook=f"Fold this event into future {event.subject} player/team trend and value analysis.",
            confidence=round(confidence, 3),
            supporting_evidence=evidence_titles,
            contradictory_evidence=[],
        )

    def assess_many(self, events: Iterable[EventRecord]) -> List[EventImpactAssessment]:
        return [self.assess(event) for event in events]
