"""Reasoning helpers for Event Timeline Intelligence."""
from __future__ import annotations

from typing import Dict, List

from Engine.EventTimeline.timeline_models import EventTimeline


def timeline_executive_summary(timeline: EventTimeline) -> str:
    if timeline.event_count == 0:
        return f"No event timeline is available for {timeline.subject}."
    if timeline.event_count == 1:
        return f"{timeline.subject} has one tracked event; Athena needs more observations before inferring a trend."
    high_nodes = [node for node in timeline.nodes if node.significance == "high"]
    if high_nodes:
        return f"{timeline.subject}'s timeline contains {len(high_nodes)} high-significance event(s), so the sequence should be treated as materially important."
    return f"{timeline.subject}'s timeline shows a related sequence of {timeline.event_count} events with no high-significance conflict detected."


def timeline_risk_flags(timeline: EventTimeline) -> List[str]:
    flags: List[str] = []
    event_types = {node.event_type for node in timeline.nodes}
    if "injury" in event_types:
        flags.append("availability_risk")
    if "trade" in event_types:
        flags.append("context_change")
    if any(node.confidence < 0.55 for node in timeline.nodes):
        flags.append("low_confidence_observation")
    if timeline.event_count < 2:
        flags.append("limited_timeline_depth")
    return flags


def timeline_reasoning_payload(timeline: EventTimeline) -> Dict[str, object]:
    return {
        "timeline_id": timeline.timeline_id,
        "subject": timeline.subject,
        "executive_summary": timeline_executive_summary(timeline),
        "risk_flags": timeline_risk_flags(timeline),
        "event_count": timeline.event_count,
        "confidence": timeline.confidence,
        "first_seen": timeline.first_seen,
        "last_seen": timeline.last_seen,
    }
