"""Source corroboration helpers for canonical events."""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List

from Engine.EventConfidence.confidence_models import CorroborationTimelineItem, SourceObservation
from Knowledge.Events.evidence_fusion import event_signature
from Knowledge.Events.models import EventRecord


def source_ids_for_event(event: EventRecord) -> List[str]:
    ids = list(event.source_ids or [])
    ids.extend(evidence.source_id for evidence in event.evidence if evidence.source_id)
    raw_source = event.raw_payload.get("source_id") if isinstance(event.raw_payload, dict) else None
    if raw_source:
        ids.append(str(raw_source))
    return sorted(set(ids))


def observations_for_event(event: EventRecord) -> List[SourceObservation]:
    observations: List[SourceObservation] = []
    for evidence in event.evidence:
        observations.append(
            SourceObservation(
                source_id=evidence.source_id,
                event_id=event.event_id,
                title=evidence.title or event.summary,
                observed_at=evidence.observed_at or event.occurred_at or "",
                confidence=evidence.confidence,
                authority=evidence.authority,
                supports_canonical=True,
            )
        )
    if not observations:
        for source_id in source_ids_for_event(event) or ["unknown"]:
            observations.append(
                SourceObservation(
                    source_id=source_id,
                    event_id=event.event_id,
                    title=event.summary,
                    observed_at=event.occurred_at or "",
                    confidence=event.confidence or 0.65,
                    supports_canonical=True,
                )
            )
    return observations


def group_events_for_corroboration(events: Iterable[EventRecord]) -> Dict[str, List[EventRecord]]:
    buckets: Dict[str, List[EventRecord]] = defaultdict(list)
    for event in events:
        buckets[event_signature(event)].append(event)
    return dict(buckets)


def detect_conflicting_events(events: Iterable[EventRecord]) -> Dict[str, List[EventRecord]]:
    """Group likely conflicts by subject/day when event types disagree materially."""

    by_subject_day: Dict[str, List[EventRecord]] = defaultdict(list)
    for event in events:
        key = f"{event.subject.lower()}|{(event.occurred_at or '')[:10]}"
        by_subject_day[key].append(event)
    conflicts: Dict[str, List[EventRecord]] = {}
    for key, bucket in by_subject_day.items():
        types = {event.event_type for event in bucket}
        if (len(types) > 1 and {"injury", "return"}.issubset(types)) or (len(types.intersection({"trade", "signing", "waiver", "claim"})) > 1):
            conflicts[key] = bucket
    return conflicts


def build_corroboration_timeline(events: Iterable[EventRecord]) -> List[CorroborationTimelineItem]:
    items: List[CorroborationTimelineItem] = []
    for event in events:
        for observation in observations_for_event(event):
            items.append(
                CorroborationTimelineItem(
                    source_id=observation.source_id,
                    event_id=event.event_id,
                    observed_at=observation.observed_at or event.occurred_at or "",
                    action="reported",
                    confidence=observation.confidence,
                )
            )
    return sorted(items, key=lambda item: (item.observed_at or "", item.source_id, item.event_id))
