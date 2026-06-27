"""Event Intelligence data models.

Knowledge owns normalized event facts and source/evidence bindings. These models
are intentionally deterministic and dependency-light so they can be reused by
Feed, Evidence, Engine, Reasoning, Studio, and validator layers.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class EventSourceProfile:
    source_id: str
    display_name: str
    source_type: str
    sport: str = "multi"
    league: str = "multi"
    authority: str = "trusted"
    reliability: float = 0.75
    freshness: float = 0.75
    opinion_weight: float = 0.0
    confidence_modifier: float = 0.0
    access_method: str = "unknown"
    notes: str = ""

    @property
    def trust_score(self) -> float:
        score = (float(self.reliability) * 0.55) + (float(self.freshness) * 0.30) + (max(0.0, 1.0 - float(self.opinion_weight)) * 0.15) + float(self.confidence_modifier)
        return max(0.0, min(1.0, round(score, 4)))

    def is_primary_fact_source(self) -> bool:
        return self.authority in {"official", "trusted"} and self.reliability >= 0.78 and self.opinion_weight <= 0.35

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["trust_score"] = self.trust_score
        data["primary_fact_source"] = self.is_primary_fact_source()
        return data


@dataclass(frozen=True)
class EventEntityLink:
    entity_id: str
    label: str = ""
    entity_type: str = "unknown"
    role: str = "subject"
    confidence: float = 0.75

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EventEvidence:
    source_id: str
    title: str
    observed_at: str
    url: str = ""
    confidence: float = 0.7
    excerpt: str = ""
    authority: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EventRecord:
    event_id: str
    event_type: str
    sport: str
    subject: str
    summary: str
    occurred_at: Optional[str] = None
    entities: List[str] = field(default_factory=list)
    evidence: List[EventEvidence] = field(default_factory=list)
    status: str = "normalized"
    confidence: float = 0.0
    raw_payload: Dict[str, Any] = field(default_factory=dict)
    league: str = "multi"
    source_ids: List[str] = field(default_factory=list)
    entity_links: List[EventEntityLink] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.source_ids and self.evidence:
            object.__setattr__(self, "source_ids", sorted({item.source_id for item in self.evidence if item.source_id}))
        if not self.entity_links and self.entities:
            object.__setattr__(self, "entity_links", [EventEntityLink(entity_id=str(entity)) for entity in self.entities])
        if not self.confidence and self.evidence:
            avg = sum(float(item.confidence) for item in self.evidence) / max(1, len(self.evidence))
            object.__setattr__(self, "confidence", round(avg, 4))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "sport": self.sport,
            "league": self.league,
            "subject": self.subject,
            "summary": self.summary,
            "occurred_at": self.occurred_at,
            "entities": list(self.entities),
            "entity_links": [item.to_dict() for item in self.entity_links],
            "source_ids": list(self.source_ids),
            "evidence": [item.to_dict() for item in self.evidence],
            "status": self.status,
            "confidence": self.confidence,
            "raw_payload": dict(self.raw_payload),
        }


@dataclass(frozen=True)
class EventGraphBinding:
    event_id: str
    node_id: str
    relationship_type: str
    confidence: float = 0.75

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EventRegistry:
    sources: Dict[str, EventSourceProfile] = field(default_factory=dict)
    events: Dict[str, EventRecord] = field(default_factory=dict)

    def register_source(self, profile: EventSourceProfile) -> None:
        if not profile.source_id:
            raise ValueError("source_id is required")
        self.sources[profile.source_id] = profile

    def register_event(self, event: EventRecord) -> None:
        if not event.event_id:
            raise ValueError("event_id is required")
        self.events[event.event_id] = event

    def source_count(self) -> int:
        return len(self.sources)

    def event_count(self) -> int:
        return len(self.events)

    def trusted_sources(self) -> List[EventSourceProfile]:
        return [source for source in self.sources.values() if source.is_primary_fact_source()]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sources": {key: value.to_dict() for key, value in sorted(self.sources.items())},
            "events": {key: value.to_dict() for key, value in sorted(self.events.items())},
        }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
