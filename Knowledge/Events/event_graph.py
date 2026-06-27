"""Bind normalized events into Athena's canonical context graph."""
from __future__ import annotations

import hashlib
from typing import Iterable

from Knowledge.Events.models import EventGraphBinding, EventRecord
from Knowledge.Events.source_intelligence import source_profile_for
from Knowledge.Graph.canonical_graph import CanonicalContextGraph, GraphNode, GraphRelationship

EVENT_GRAPH_VERSION = "0.5.1.4.0"


def _safe_id(prefix: str, value: str) -> str:
    text = str(value or "unknown").strip().lower()
    return f"{prefix}_" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def bind_event_to_graph(event: EventRecord, graph: CanonicalContextGraph | None = None) -> tuple[CanonicalContextGraph, EventGraphBinding]:
    active = graph or CanonicalContextGraph(metadata={"event_graph_version": EVENT_GRAPH_VERSION})
    event_node_id = f"event:{event.event_id}"
    active.add_node(GraphNode(
        id=event_node_id,
        type="event",
        label=event.summary,
        evidence_type="event",
        source="event_registry",
        confidence=event.confidence,
        properties={
            "event_id": event.event_id,
            "event_type": event.event_type,
            "sport": event.sport,
            "subject": event.subject,
            "occurred_at": event.occurred_at,
            "status": event.status,
        },
    ))

    source_nodes: list[str] = []
    evidence_nodes: list[str] = []
    entity_nodes: list[str] = []
    rel_ids: list[str] = []

    for evidence in event.evidence:
        profile = source_profile_for(evidence.source_id)
        source_node_id = f"source:{profile.source_id}"
        source_nodes.append(source_node_id)
        active.add_node(GraphNode(
            id=source_node_id,
            type="source",
            label=profile.display_name,
            evidence_type="source_profile",
            source="source_registry",
            confidence=profile.trust_score,
            properties=profile.to_dict(),
        ))
        rel_id = f"rel:{event.event_id}:reported_by:{profile.source_id}"
        active.add_relationship(GraphRelationship(rel_id, event_node_id, source_node_id, "reported_by", source="event_registry", confidence=evidence.confidence, properties={"observed_at": evidence.observed_at}))
        rel_ids.append(rel_id)

        evidence_node_id = _safe_id("evidence", f"{event.event_id}|{evidence.source_id}|{evidence.title}")
        evidence_nodes.append(evidence_node_id)
        active.add_node(GraphNode(
            id=evidence_node_id,
            type="evidence",
            label=evidence.title,
            evidence_type="event_evidence",
            source=evidence.source_id,
            confidence=evidence.confidence,
            properties=evidence.to_dict(),
        ))
        ev_rel_id = f"rel:{event.event_id}:supported_by:{evidence_node_id}"
        active.add_relationship(GraphRelationship(ev_rel_id, event_node_id, evidence_node_id, "supported_by", source=evidence.source_id, confidence=evidence.confidence))
        rel_ids.append(ev_rel_id)

    for link in event.entity_links:
        entity_node_id = link.entity_id if link.entity_id.startswith("entity:") else f"entity:{link.entity_id}"
        entity_nodes.append(entity_node_id)
        active.add_node(GraphNode(
            id=entity_node_id,
            type=link.entity_type if link.entity_type != "unknown" else "entity",
            label=link.label,
            evidence_type="event_entity",
            source="event_registry",
            confidence=link.confidence,
            properties=link.to_dict(),
        ))
        ent_rel_id = f"rel:{link.entity_id}:participated_in:{event.event_id}:{link.role}"
        active.add_relationship(GraphRelationship(ent_rel_id, entity_node_id, event_node_id, "participated_in", source="event_registry", confidence=link.confidence, properties={"role": link.role}))
        rel_ids.append(ent_rel_id)

    binding = EventGraphBinding(
        event_node_id=event_node_id,
        source_node_ids=sorted(set(source_nodes)),
        entity_node_ids=sorted(set(entity_nodes)),
        evidence_node_ids=sorted(set(evidence_nodes)),
        relationship_ids=sorted(set(rel_ids)),
    )
    return active, binding


def bind_events_to_graph(events: Iterable[EventRecord], graph: CanonicalContextGraph | None = None) -> CanonicalContextGraph:
    active = graph or CanonicalContextGraph(metadata={"event_graph_version": EVENT_GRAPH_VERSION})
    for event in events:
        bind_event_to_graph(event, active)
    return active
