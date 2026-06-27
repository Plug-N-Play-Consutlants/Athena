"""Models for Athena 0.5.2.5.0 Event Summarization Engine."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

EVENT_SUMMARIZATION_MODEL_VERSION = "0.5.2.5.0"


@dataclass(frozen=True)
class EventSummaryItem:
    """One concise Scout-ready summary item for an event or timeline node."""

    event_id: str
    subject: str
    event_type: str
    headline: str
    summary: str
    occurred_at: Optional[str] = None
    confidence_label: str = "developing"
    confidence_score: int = 0
    significance: str = "moderate"
    source_ids: List[str] = field(default_factory=list)
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EventExecutiveBrief:
    """High-level narrative brief produced from an event set."""

    brief_id: str
    title: str
    executive_summary: str
    what_changed: str
    confidence_summary: str
    timeline_summary: str = ""
    items: List[EventSummaryItem] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def item_count(self) -> int:
        return len(self.items)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "brief_id": self.brief_id,
            "title": self.title,
            "executive_summary": self.executive_summary,
            "what_changed": self.what_changed,
            "confidence_summary": self.confidence_summary,
            "timeline_summary": self.timeline_summary,
            "item_count": self.item_count,
            "items": [item.to_dict() for item in self.items],
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class EventSummaryBatch:
    """Batch output from Event Summarization."""

    version: str
    brief: EventExecutiveBrief
    scout_payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "brief": self.brief.to_dict(),
            "scout_payload": dict(self.scout_payload),
        }
