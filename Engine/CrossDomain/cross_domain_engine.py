"""Cross-domain Event Impact Engine.

This engine propagates event reasoning into the domains Athena already reasons
about. It produces deterministic impact records and graph deltas; it does not
mutate persistent Knowledge stores directly.
"""
from __future__ import annotations

from typing import Iterable, List

from Engine.CrossDomain.domain_router import normalize_domains
from Engine.CrossDomain.graph_delta_builder import build_graph_deltas
from Engine.CrossDomain.impact_models import DomainImpact, PropagationResult
from Engine.CrossDomain.impact_rules import domains_for_event_type
from Knowledge.Events.models import EventRecord


SEVERITY_BY_EVENT_TYPE = {
    "injury": "high",
    "trade": "high",
    "suspension": "medium",
    "call_up": "medium",
    "send_down": "medium",
    "demotion": "medium",
    "free_agent_signing": "medium",
    "signing": "medium",
    "waiver": "medium",
    "claim": "medium",
    "schedule_change": "low",
    "game_result": "low",
}


class CrossDomainImpactEngine:
    """Routes canonical events into player/team/fantasy/org impacts."""

    def domains_for_event(self, event: EventRecord) -> List[str]:
        return normalize_domains(domains_for_event_type(event.event_type))

    def impact_for_domain(self, event: EventRecord, domain: str) -> DomainImpact:
        confidence = round(max(0.35, min(0.98, event.confidence or 0.65)), 3)
        severity = SEVERITY_BY_EVENT_TYPE.get(event.event_type, "low")
        entity_id = f"{domain}:{event.subject.lower().replace(' ', '_')}"
        rationale = f"{event.event_type} event involving {event.subject} changes {domain} context."
        if domain == "fantasy":
            rationale = f"{event.event_type} event may change fantasy value, availability, role, or schedule context for {event.subject}."
        elif domain == "team":
            rationale = f"{event.event_type} event may affect roster construction, depth, usage, or organizational direction."
        elif domain == "player":
            rationale = f"{event.event_type} event may affect player role, availability, trend context, or future evaluation."
        return DomainImpact(
            domain=domain,
            entity_id=entity_id,
            entity_label=event.subject,
            impact_type=event.event_type,
            severity=severity,
            confidence=confidence,
            rationale=rationale,
        )

    def propagate(self, event: EventRecord) -> PropagationResult:
        domains = self.domains_for_event(event)
        impacts = [self.impact_for_domain(event, domain) for domain in domains]
        deltas = build_graph_deltas(event, impacts)
        confidence = round(sum(impact.confidence for impact in impacts) / max(1, len(impacts)), 3)
        return PropagationResult(
            event_id=event.event_id,
            event_type=event.event_type,
            subject=event.subject,
            impacts=impacts,
            graph_deltas=deltas,
            confidence=confidence,
            status="propagated",
        )

    def propagate_many(self, events: Iterable[EventRecord]) -> List[PropagationResult]:
        return [self.propagate(event) for event in events]
