"""Build Knowledge Graph deltas from event propagation impacts."""
from __future__ import annotations

from typing import Iterable, List

from Engine.CrossDomain.impact_models import DomainImpact, GraphDelta
from Knowledge.Events.models import EventRecord


RELATIONSHIP_BY_DOMAIN = {
    "player": "affects_player",
    "team": "affects_team",
    "prospect": "affects_prospect",
    "fantasy": "affects_fantasy_value",
    "historical": "adds_historical_context",
    "organization": "affects_organization",
}


def build_graph_deltas(event: EventRecord, impacts: Iterable[DomainImpact]) -> List[GraphDelta]:
    deltas: List[GraphDelta] = []
    for impact in impacts:
        deltas.append(GraphDelta(
            source_event_id=event.event_id,
            relationship_type=RELATIONSHIP_BY_DOMAIN.get(impact.domain, "affects"),
            source_entity=event.subject,
            target_entity=impact.entity_id,
            confidence=impact.confidence,
            provenance=f"event:{event.event_id}",
        ))
    return deltas
