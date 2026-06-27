"""Event Timeline Intelligence models for Athena 0.5.2.3.0."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

EVENT_TIMELINE_MODEL_VERSION = "0.5.2.3.0"


def _parse_time(value: Optional[str]) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class TimelineNode:
    """A normalized event observation positioned on a timeline."""

    node_id: str
    event_id: str
    event_type: str
    subject: str
    summary: str
    occurred_at: Optional[str] = None
    source_ids: List[str] = field(default_factory=list)
    confidence: float = 0.0
    significance: str = "low"
    sequence_index: int = 0
    reasoning_summary: str = ""

    @property
    def sort_key(self) -> datetime:
        return _parse_time(self.occurred_at)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TimelineLink:
    """Relationship between two timeline nodes."""

    from_node_id: str
    to_node_id: str
    relationship: str
    rationale: str
    confidence: float = 0.65

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EventTimeline:
    """A coherent chain of related events for one subject/context."""

    timeline_id: str
    subject: str
    nodes: List[TimelineNode] = field(default_factory=list)
    links: List[TimelineLink] = field(default_factory=list)
    headline: str = ""
    narrative: str = ""
    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)

    @property
    def event_count(self) -> int:
        return len(self.nodes)

    @property
    def first_seen(self) -> Optional[str]:
        if not self.nodes:
            return None
        return self.nodes[0].occurred_at

    @property
    def last_seen(self) -> Optional[str]:
        if not self.nodes:
            return None
        return self.nodes[-1].occurred_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timeline_id": self.timeline_id,
            "subject": self.subject,
            "event_count": self.event_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "headline": self.headline,
            "narrative": self.narrative,
            "confidence": self.confidence,
            "nodes": [node.to_dict() for node in self.nodes],
            "links": [link.to_dict() for link in self.links],
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class TimelineBuildResult:
    """Batch output from Event Timeline Intelligence."""

    version: str
    timelines: List[EventTimeline] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def timeline_count(self) -> int:
        return len(self.timelines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "timeline_count": self.timeline_count,
            "timelines": [timeline.to_dict() for timeline in self.timelines],
            "warnings": list(self.warnings),
        }
