"""Models for Athena 0.5.2.4.0 Event Confidence & Source Corroboration."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

EVENT_CONFIDENCE_MODEL_VERSION = "0.5.2.4.0"


@dataclass(frozen=True)
class SourceConfidenceProfile:
    """Normalized source-quality profile used by confidence scoring."""

    source_id: str
    display_name: str = "Unknown Source"
    authority: str = "trusted"
    reliability: float = 0.75
    timeliness: float = 0.75
    completeness: float = 0.75
    availability: float = 0.75
    opinion_weight: float = 0.0
    corroboration_weight: float = 1.0

    @property
    def trust_score(self) -> float:
        authority_bonus = 0.08 if self.authority == "official" else 0.03 if self.authority in {"wire", "trusted_newswire"} else 0.0
        opinion_penalty = max(0.0, min(0.35, self.opinion_weight * 0.35))
        base = (
            (self.reliability * 0.35)
            + (self.timeliness * 0.20)
            + (self.completeness * 0.20)
            + (self.availability * 0.15)
            + (self.corroboration_weight * 0.10)
            + authority_bonus
            - opinion_penalty
        )
        return round(max(0.0, min(1.0, base)), 3)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["trust_score"] = self.trust_score
        return data


@dataclass(frozen=True)
class SourceObservation:
    """One source's observation of a canonical event."""

    source_id: str
    event_id: str
    title: str
    observed_at: str = ""
    confidence: float = 0.7
    authority: str = "trusted"
    supports_canonical: bool = True
    conflict_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConfidenceExplanation:
    """Human-readable confidence rationale exposed to Scout/Studio."""

    label: str
    score: int
    summary: str
    factors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EventConfidenceResult:
    """Confidence score and provenance for a single canonical event."""

    event_id: str
    subject: str
    event_type: str
    score: int
    label: str
    source_ids: List[str] = field(default_factory=list)
    supporting_sources: List[str] = field(default_factory=list)
    conflicting_sources: List[str] = field(default_factory=list)
    corroborated: bool = False
    conflict_detected: bool = False
    explanation: ConfidenceExplanation | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "subject": self.subject,
            "event_type": self.event_type,
            "score": self.score,
            "label": self.label,
            "source_ids": list(self.source_ids),
            "supporting_sources": list(self.supporting_sources),
            "conflicting_sources": list(self.conflicting_sources),
            "corroborated": self.corroborated,
            "conflict_detected": self.conflict_detected,
            "explanation": self.explanation.to_dict() if self.explanation else None,
        }


@dataclass(frozen=True)
class CorroborationTimelineItem:
    source_id: str
    event_id: str
    observed_at: str
    action: str = "observed"
    confidence: float = 0.7

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SourceCorroborationResult:
    """Batch result for confidence/corroboration scoring."""

    version: str
    results: List[EventConfidenceResult] = field(default_factory=list)
    timeline: List[CorroborationTimelineItem] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def result_count(self) -> int:
        return len(self.results)

    @property
    def corroborated_count(self) -> int:
        return sum(1 for result in self.results if result.corroborated)

    @property
    def conflict_count(self) -> int:
        return sum(1 for result in self.results if result.conflict_detected)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "result_count": self.result_count,
            "corroborated_count": self.corroborated_count,
            "conflict_count": self.conflict_count,
            "results": [result.to_dict() for result in self.results],
            "timeline": [item.to_dict() for item in self.timeline],
            "warnings": list(self.warnings),
        }
