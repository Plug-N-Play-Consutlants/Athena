"""Deterministic event payload normalizer.

Provider/build payloads are converted into Athena's canonical EventRecord
contract. The normalizer assigns source-weighted evidence confidence but does
not produce conclusions or recommendations.
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List

from Knowledge.Events.models import EventEntityLink, EventEvidence, EventRecord, utc_now_iso
from Knowledge.Events.registry import canonical_event_type
from Knowledge.Events.source_intelligence import score_source_confidence, source_profile_for


def _clean(value: Any, default: str = "") -> str:
    text = str(value or default).strip()
    return " ".join(text.split())


def _event_id(payload: Dict[str, Any]) -> str:
    provided = _clean(payload.get("event_id") or payload.get("id"))
    if provided:
        return provided
    basis = "|".join([
        canonical_event_type(_clean(payload.get("event_type"), "event")),
        _clean(payload.get("sport"), "multi"),
        _clean(payload.get("subject")),
        _clean(payload.get("summary") or payload.get("title")),
        _clean(payload.get("occurred_at") or payload.get("published_at")),
    ])
    return "evt_" + hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]


def _evidence(payload: Dict[str, Any]) -> List[EventEvidence]:
    raw_items = payload.get("evidence") or []
    if isinstance(raw_items, dict):
        raw_items = [raw_items]
    items: List[EventEvidence] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        source_id = _clean(item.get("source_id") or payload.get("source_id"), "unknown")
        profile = source_profile_for(source_id)
        base = float(item.get("confidence", payload.get("source_confidence", 0.65)) or 0.65)
        items.append(EventEvidence(
            source_id=source_id,
            title=_clean(item.get("title") or payload.get("title") or payload.get("summary"), "Untitled event"),
            observed_at=_clean(item.get("observed_at") or payload.get("published_at"), utc_now_iso()),
            url=_clean(item.get("url") or payload.get("url")),
            confidence=score_source_confidence(source_id, base),
            excerpt=_clean(item.get("excerpt") or payload.get("excerpt")),
            authority=profile.authority,
        ))
    if not items:
        source_id = _clean(payload.get("source_id"), "unknown")
        profile = source_profile_for(source_id)
        base = float(payload.get("source_confidence", 0.65) or 0.65)
        items.append(EventEvidence(
            source_id=source_id,
            title=_clean(payload.get("title") or payload.get("summary"), "Untitled event"),
            observed_at=_clean(payload.get("published_at") or payload.get("observed_at"), utc_now_iso()),
            url=_clean(payload.get("url")),
            confidence=score_source_confidence(source_id, base),
            excerpt=_clean(payload.get("excerpt")),
            authority=profile.authority,
        ))
    return items


def _entity_links(payload: Dict[str, Any]) -> List[EventEntityLink]:
    raw = payload.get("entity_links") or []
    links: List[EventEntityLink] = []
    if isinstance(raw, dict):
        raw = [raw]
    for item in raw:
        if not isinstance(item, dict):
            continue
        label = _clean(item.get("label") or item.get("name") or item.get("entity_id"))
        entity_id = _clean(item.get("entity_id") or label.lower().replace(" ", "_"))
        if not entity_id:
            continue
        links.append(EventEntityLink(
            entity_id=entity_id,
            label=label or entity_id,
            role=_clean(item.get("role"), "participant"),
            entity_type=_clean(item.get("entity_type"), "unknown"),
            confidence=float(item.get("confidence", 0.75) or 0.75),
        ))
    entities = payload.get("entities") or []
    if isinstance(entities, str):
        entities = [entities]
    existing = {link.label.lower() for link in links}
    for label_raw in entities:
        label = _clean(label_raw)
        if label and label.lower() not in existing:
            links.append(EventEntityLink(entity_id="entity_" + hashlib.sha1(label.lower().encode("utf-8")).hexdigest()[:12], label=label))
    return links


def normalize_event_payload(payload: Dict[str, Any]) -> EventRecord:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a dictionary")
    event_type = canonical_event_type(_clean(payload.get("event_type"), "event"))
    evidence = _evidence(payload)
    confidence = max(0.0, min(1.0, sum(item.confidence for item in evidence) / max(1, len(evidence))))
    entity_links = _entity_links(payload)
    entities = payload.get("entities") or [link.label for link in entity_links]
    if isinstance(entities, str):
        entities = [entities]
    source_ids = sorted({item.source_id for item in evidence if item.source_id})
    return EventRecord(
        event_id=_event_id({**payload, "event_type": event_type}),
        event_type=event_type,
        sport=_clean(payload.get("sport"), "multi"),
        league=_clean(payload.get("league"), "multi"),
        subject=_clean(payload.get("subject") or payload.get("entity") or payload.get("team") or payload.get("player"), "unknown"),
        summary=_clean(payload.get("summary") or payload.get("title"), "Event summary unavailable"),
        occurred_at=_clean(payload.get("occurred_at") or payload.get("published_at")) or None,
        entities=[_clean(item) for item in entities if _clean(item)],
        entity_links=entity_links,
        evidence=evidence,
        status="normalized",
        confidence=confidence,
        source_ids=source_ids,
        raw_payload=dict(payload),
    )


def canonical_event_payload(payload: Dict[str, Any]) -> EventRecord:
    """Compatibility alias for older Event Intelligence import paths."""
    return normalize_event_payload(payload)
