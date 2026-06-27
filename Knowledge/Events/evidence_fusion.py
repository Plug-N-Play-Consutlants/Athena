"""Multi-source evidence fusion for Athena Event Intelligence.

This module turns multiple normalized EventRecord observations into
provenance-preserving fused evidence records. It remains in the Knowledge layer:
it scores evidence quality and source agreement, but it does not produce sports
advice or reasoning conclusions.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from Knowledge.Events.models import EventEvidence, EventRecord, EventSourceProfile
from Knowledge.Events.source_intelligence import SourceRegistry, seed_source_registry, source_profile_for

EVIDENCE_FUSION_VERSION = "0.5.1.5.0"
RESOLUTION_STATES = ["corroborated", "single_source", "conflicted", "unresolved"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}:" + hashlib.sha1(str(value).encode("utf-8")).hexdigest()[:16]


def event_fusion_key(event: EventRecord) -> str:
    """Return a stable duplicate-detection key for a normalized event."""
    entity_key = ",".join(sorted(str(entity).lower() for entity in (event.entities or [])))
    if not entity_key and event.entity_links:
        entity_key = ",".join(sorted(link.entity_id.lower() for link in event.entity_links))
    occurred_key = (event.occurred_at or "unknown")[:10]
    subject_key = (event.subject or "unknown").strip().lower()
    raw = "|".join([
        (event.sport or "multi").lower(),
        (event.event_type or "event").lower(),
        subject_key,
        entity_key,
        occurred_key,
    ])
    return _stable_id("fusion", raw)


@dataclass(frozen=True)
class SourceConfidenceProfile:
    source_id: str
    display_name: str
    authority: str
    reliability: float
    freshness: float
    timeliness: float = 0.75
    completeness: float = 0.75
    availability: float = 0.75
    trust_score: float = 0.75
    weight: float = 0.75

    @classmethod
    def from_source_profile(cls, profile: EventSourceProfile) -> "SourceConfidenceProfile":
        trust = clamp(profile.trust_score)
        weight = clamp((trust * 0.6) + (float(profile.reliability) * 0.25) + (float(profile.freshness) * 0.15))
        return cls(
            source_id=profile.source_id,
            display_name=profile.display_name,
            authority=profile.authority,
            reliability=clamp(profile.reliability),
            freshness=clamp(profile.freshness),
            timeliness=clamp(profile.freshness),
            completeness=clamp(profile.reliability),
            availability=0.85 if profile.access_method in {"api", "feed", "rss", "provider"} else 0.65,
            trust_score=trust,
            weight=weight,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceObservation:
    observation_id: str
    event_id: str
    source_id: str
    source_weight: float
    confidence: float
    observed_at: str
    title: str
    summary: str
    url: str = ""
    authority: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FusedEvidenceRecord:
    fused_id: str
    canonical_event_id: str
    event_type: str
    sport: str
    subject: str
    summary: str
    first_seen_at: str
    last_updated_at: str
    confidence: float
    source_ids: List[str] = field(default_factory=list)
    supporting_evidence: List[EvidenceObservation] = field(default_factory=list)
    conflicting_evidence: List[EvidenceObservation] = field(default_factory=list)
    resolution_state: str = "single_source"
    event_ids: List[str] = field(default_factory=list)

    @property
    def corroborated(self) -> bool:
        return len(set(self.source_ids)) >= 2 and self.resolution_state == "corroborated"

    @property
    def resolution_status(self) -> str:
        """Compatibility alias for pre-0.5.3.1 callers."""
        return self.resolution_state

    @property
    def canonical_event(self) -> EventRecord:
        """Return a lightweight canonical EventRecord for older engines/tests."""
        evidence = [
            EventEvidence(
                source_id=item.source_id,
                title=item.title,
                observed_at=item.observed_at,
                url=item.url,
                confidence=item.confidence,
                authority=item.authority,
            )
            for item in self.supporting_evidence
        ]
        return EventRecord(
            event_id=self.canonical_event_id,
            event_type=self.event_type,
            sport=self.sport,
            subject=self.subject,
            summary=self.summary,
            occurred_at=self.first_seen_at,
            entities=[],
            evidence=evidence,
            status="fused",
            confidence=self.confidence,
            source_ids=list(self.source_ids),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fused_id": self.fused_id,
            "canonical_event_id": self.canonical_event_id,
            "event_type": self.event_type,
            "sport": self.sport,
            "subject": self.subject,
            "summary": self.summary,
            "first_seen_at": self.first_seen_at,
            "last_updated_at": self.last_updated_at,
            "confidence": self.confidence,
            "source_ids": list(self.source_ids),
            "supporting_evidence": [item.to_dict() for item in self.supporting_evidence],
            "conflicting_evidence": [item.to_dict() for item in self.conflicting_evidence],
            "resolution_state": self.resolution_state,
            "event_ids": list(self.event_ids),
            "corroborated": self.corroborated,
        }


@dataclass(frozen=True)
class FusionResult:
    version: str
    fused_records: List[FusedEvidenceRecord] = field(default_factory=list)
    source_profiles: Dict[str, SourceConfidenceProfile] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    @property
    def fused_count(self) -> int:
        return len(self.fused_records)

    @property
    def conflict_count(self) -> int:
        return sum(1 for item in self.fused_records if item.conflicting_evidence)

    @property
    def corroborated_count(self) -> int:
        return sum(1 for item in self.fused_records if item.corroborated)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "fused_count": self.fused_count,
            "conflict_count": self.conflict_count,
            "corroborated_count": self.corroborated_count,
            "fused_records": [item.to_dict() for item in self.fused_records],
            "source_profiles": {key: value.to_dict() for key, value in sorted(self.source_profiles.items())},
            "warnings": list(self.warnings),
        }


class EvidenceFusionEngine:
    """Merge duplicate event observations while preserving provenance."""

    def __init__(self, source_registry: Optional[SourceRegistry] = None) -> None:
        self.source_registry = source_registry or seed_source_registry()

    def source_confidence(self, source_id: str) -> SourceConfidenceProfile:
        return SourceConfidenceProfile.from_source_profile(source_profile_for(source_id, self.source_registry))

    def observation_from_event(self, event: EventRecord, evidence: Optional[EventEvidence] = None) -> EvidenceObservation:
        source_id = evidence.source_id if evidence else (event.source_ids[0] if event.source_ids else "unknown")
        profile = self.source_confidence(source_id)
        evidence_confidence = evidence.confidence if evidence else event.confidence
        confidence = clamp((float(evidence_confidence) * 0.55) + (profile.weight * 0.45))
        title = evidence.title if evidence else event.summary
        observed_at = evidence.observed_at if evidence else (event.occurred_at or utc_now_iso())
        raw = f"{event.event_id}|{source_id}|{title}|{observed_at}"
        return EvidenceObservation(
            observation_id=_stable_id("observation", raw),
            event_id=event.event_id,
            source_id=source_id,
            source_weight=profile.weight,
            confidence=round(confidence, 4),
            observed_at=observed_at,
            title=title,
            summary=event.summary,
            url=evidence.url if evidence else "",
            authority=profile.authority,
        )

    def _observations_for(self, event: EventRecord) -> List[EvidenceObservation]:
        if event.evidence:
            return [self.observation_from_event(event, evidence) for evidence in event.evidence]
        return [self.observation_from_event(event, None)]

    def _confidence_for(self, observations: List[EvidenceObservation], conflict_count: int = 0) -> float:
        if not observations:
            return 0.0
        total_weight = sum(max(item.source_weight, 0.01) for item in observations)
        weighted = sum(item.confidence * max(item.source_weight, 0.01) for item in observations) / total_weight
        source_count = len({item.source_id for item in observations})
        corroboration_boost = min(0.12, max(0, source_count - 1) * 0.04)
        conflict_penalty = min(0.25, conflict_count * 0.08)
        return round(clamp(weighted + corroboration_boost - conflict_penalty), 4)

    def fuse(self, events: Iterable[EventRecord]) -> FusionResult:
        groups: Dict[str, List[EventRecord]] = {}
        for event in events:
            groups.setdefault(event_fusion_key(event), []).append(event)

        fused: List[FusedEvidenceRecord] = []
        source_profiles: Dict[str, SourceConfidenceProfile] = {}
        warnings: List[str] = []

        for key, grouped_events in sorted(groups.items()):
            primary = sorted(grouped_events, key=lambda item: item.event_id)[0]
            observations: List[EvidenceObservation] = []
            for event in grouped_events:
                observations.extend(self._observations_for(event))
            for observation in observations:
                source_profiles.setdefault(observation.source_id, self.source_confidence(observation.source_id))

            distinct_sources = sorted({item.source_id for item in observations})
            conflicting: List[EvidenceObservation] = []
            supporting = observations
            if len({event.summary.strip().lower() for event in grouped_events if event.summary}) > 1 and len(distinct_sources) > 1:
                # Different wording is preserved as supporting evidence, not treated as a factual conflict.
                warnings.append(f"Multiple summaries preserved for {key}")

            state = "corroborated" if len(distinct_sources) >= 2 else "single_source"
            confidence = self._confidence_for(supporting, len(conflicting))
            observed_times = sorted(item.observed_at for item in observations if item.observed_at)
            fused.append(FusedEvidenceRecord(
                fused_id=key,
                canonical_event_id=primary.event_id,
                event_type=primary.event_type,
                sport=primary.sport,
                subject=primary.subject,
                summary=primary.summary,
                first_seen_at=observed_times[0] if observed_times else utc_now_iso(),
                last_updated_at=observed_times[-1] if observed_times else utc_now_iso(),
                confidence=confidence,
                source_ids=distinct_sources,
                supporting_evidence=supporting,
                conflicting_evidence=conflicting,
                resolution_state=state,
                event_ids=sorted({event.event_id for event in grouped_events}),
            ))

        return FusionResult(version=EVIDENCE_FUSION_VERSION, fused_records=fused, source_profiles=source_profiles, warnings=warnings)

    def detect_conflicts(self, events: Iterable[EventRecord]) -> List[FusedEvidenceRecord]:
        """Detect same-subject same-date factual conflicts across event types."""
        buckets: Dict[Tuple[str, str, str], List[EventRecord]] = {}
        for event in events:
            buckets.setdefault(((event.sport or "multi").lower(), (event.subject or "unknown").lower(), (event.occurred_at or "unknown")[:10]), []).append(event)

        conflicts: List[FusedEvidenceRecord] = []
        for _, bucket in buckets.items():
            types = {event.event_type for event in bucket}
            if len(types) <= 1:
                continue
            observations: List[EvidenceObservation] = []
            for event in bucket:
                observations.extend(self._observations_for(event))
            primary = sorted(bucket, key=lambda item: item.event_id)[0]
            conflicts.append(FusedEvidenceRecord(
                fused_id=_stable_id("conflict", "|".join(sorted(event.event_id for event in bucket))),
                canonical_event_id=primary.event_id,
                event_type=primary.event_type,
                sport=primary.sport,
                subject=primary.subject,
                summary=f"Conflicting event classifications for {primary.subject}",
                first_seen_at=min(item.observed_at for item in observations),
                last_updated_at=max(item.observed_at for item in observations),
                confidence=self._confidence_for(observations, len(observations)),
                source_ids=sorted({item.source_id for item in observations}),
                supporting_evidence=[],
                conflicting_evidence=observations,
                resolution_state="conflicted",
                event_ids=sorted({event.event_id for event in bucket}),
            ))
        return conflicts


def fuse_event_evidence(events: Iterable[EventRecord], source_registry: Optional[SourceRegistry] = None) -> FusionResult:
    return EvidenceFusionEngine(source_registry).fuse(events)


def evidence_fusion_summary(events: Iterable[EventRecord]) -> Dict[str, Any]:
    return fuse_event_evidence(events).to_dict()


def event_signature(event: EventRecord) -> str:
    """Compatibility alias for the stable event fusion key."""
    return event_fusion_key(event)


def fuse_events(events: Iterable[EventRecord], source_registry: Optional[SourceRegistry] = None) -> List[FusedEvidenceRecord]:
    """Compatibility wrapper returning fused records directly.

    Newer code can use fuse_event_evidence(...) for the full FusionResult. Older
    validators and event engines expect list-like fused records.
    """
    return fuse_event_evidence(events, source_registry).fused_records


FusedEvidence = FusedEvidenceRecord
