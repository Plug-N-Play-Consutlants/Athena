"""Models for Athena Live Event Reasoning."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

EVENT_REASONING_MODEL_VERSION = "0.5.2.1.1"


@dataclass(frozen=True)
class EventImpactAssessment:
    immediate: str
    short_term: str
    long_term: str
    affected_domains: List[str] = field(default_factory=list)
    significance: str = "moderate"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EventReasoningResult:
    reasoning_id: str
    event_id: str
    event_type: str
    subject: str
    executive_summary: str
    impact: EventImpactAssessment
    confidence: float
    supporting_evidence: List[str] = field(default_factory=list)
    conflicting_evidence: List[str] = field(default_factory=list)
    reasoning_trace: List[str] = field(default_factory=list)
    source_ids: List[str] = field(default_factory=list)
    timeline_hint: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reasoning_id": self.reasoning_id,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "subject": self.subject,
            "executive_summary": self.executive_summary,
            "impact": self.impact.to_dict(),
            "confidence": self.confidence,
            "supporting_evidence": list(self.supporting_evidence),
            "conflicting_evidence": list(self.conflicting_evidence),
            "reasoning_trace": list(self.reasoning_trace),
            "source_ids": list(self.source_ids),
            "timeline_hint": self.timeline_hint,
        }


@dataclass(frozen=True)
class EventReasoningBatch:
    version: str
    results: List[EventReasoningResult] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def result_count(self) -> int:
        return len(self.results)

    @property
    def high_impact_count(self) -> int:
        return sum(1 for result in self.results if result.impact.significance in {"high", "major"})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "result_count": self.result_count,
            "high_impact_count": self.high_impact_count,
            "results": [item.to_dict() for item in self.results],
            "warnings": list(self.warnings),
        }
