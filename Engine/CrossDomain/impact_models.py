"""Models for cross-domain event propagation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class DomainImpact:
    domain: str
    entity_id: str
    entity_label: str
    impact_type: str
    severity: str
    confidence: float
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class GraphDelta:
    source_event_id: str
    relationship_type: str
    source_entity: str
    target_entity: str
    confidence: float
    provenance: str

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class PropagationResult:
    event_id: str
    event_type: str
    subject: str
    impacts: List[DomainImpact] = field(default_factory=list)
    graph_deltas: List[GraphDelta] = field(default_factory=list)
    confidence: float = 0.0
    status: str = "propagated"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "subject": self.subject,
            "impacts": [impact.to_dict() for impact in self.impacts],
            "graph_deltas": [delta.to_dict() for delta in self.graph_deltas],
            "confidence": self.confidence,
            "status": self.status,
        }
