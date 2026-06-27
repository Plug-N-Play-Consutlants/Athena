"""Timeline construction engine for related Athena events."""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Sequence

from Engine.EventTimeline.timeline_models import EventTimeline, TimelineBuildResult, TimelineLink, TimelineNode
from Knowledge.Events.models import EventRecord

EVENT_TIMELINE_ENGINE_VERSION = "0.5.2.3.0"

HIGH_SIGNIFICANCE = {"trade", "injury", "suspension", "retirement", "coaching_change"}
MEDIUM_SIGNIFICANCE = {"signing", "free_agent_signing", "waiver", "claim", "call_up", "send_down", "demotion"}


def _safe_subject(event: EventRecord) -> str:
    if event.subject:
        return event.subject
    if event.entities:
        return event.entities[0]
    return "unknown"


def significance_for_event(event: EventRecord) -> str:
    if event.event_type in HIGH_SIGNIFICANCE:
        return "high"
    if event.event_type in MEDIUM_SIGNIFICANCE:
        return "medium"
    return "low"


def source_ids_for_event(event: EventRecord) -> List[str]:
    return sorted({evidence.source_id for evidence in event.evidence if evidence.source_id})


def group_events_by_subject(events: Iterable[EventRecord]) -> Dict[str, List[EventRecord]]:
    groups: Dict[str, List[EventRecord]] = defaultdict(list)
    for event in events:
        groups[_safe_subject(event)].append(event)
    return dict(groups)


def build_timeline_nodes(events: Sequence[EventRecord]) -> List[TimelineNode]:
    ordered = sorted(events, key=lambda item: ((item.occurred_at or ""), item.event_id))
    nodes: List[TimelineNode] = []
    for idx, event in enumerate(ordered, start=1):
        nodes.append(
            TimelineNode(
                node_id=f"timeline_node:{event.event_id}",
                event_id=event.event_id,
                event_type=event.event_type,
                subject=_safe_subject(event),
                summary=event.summary,
                occurred_at=event.occurred_at,
                source_ids=source_ids_for_event(event),
                confidence=round(max(0.0, min(1.0, event.confidence or 0.5)), 3),
                significance=significance_for_event(event),
                sequence_index=idx,
                reasoning_summary=f"{event.event_type} event positioned at sequence step {idx} for {_safe_subject(event)}.",
            )
        )
    return nodes


def build_timeline_links(nodes: Sequence[TimelineNode]) -> List[TimelineLink]:
    links: List[TimelineLink] = []
    for before, after in zip(nodes, nodes[1:]):
        confidence = round(max(0.45, min(0.95, (before.confidence + after.confidence) / 2)), 3)
        links.append(
            TimelineLink(
                from_node_id=before.node_id,
                to_node_id=after.node_id,
                relationship="followed_by",
                rationale=f"{after.event_type} followed {before.event_type} in the {after.subject} event sequence.",
                confidence=confidence,
            )
        )
    return links


def build_timeline_narrative(subject: str, nodes: Sequence[TimelineNode]) -> tuple[str, str]:
    if not nodes:
        return f"No timeline available for {subject}.", "No related events were available."
    headline = f"{subject}: {len(nodes)} related event{'s' if len(nodes) != 1 else ''} tracked"
    first = nodes[0]
    last = nodes[-1]
    if len(nodes) == 1:
        narrative = f"Athena currently has one event for {subject}: {first.summary}"
    else:
        narrative = (
            f"Athena traces {subject} from {first.event_type} through {last.event_type}. "
            f"The sequence starts with: {first.summary} It currently ends with: {last.summary}"
        )
    return headline, narrative


class EventTimelineEngine:
    """Builds coherent timelines from canonical EventRecord objects."""

    version = EVENT_TIMELINE_ENGINE_VERSION

    def build_for_subject(self, subject: str, events: Sequence[EventRecord]) -> EventTimeline:
        nodes = build_timeline_nodes(events)
        links = build_timeline_links(nodes)
        headline, narrative = build_timeline_narrative(subject, nodes)
        if nodes:
            confidence = round(sum(node.confidence for node in nodes) / len(nodes), 3)
        else:
            confidence = 0.0
        warnings: List[str] = []
        if len(nodes) < 2:
            warnings.append("Timeline has fewer than two events; narrative confidence is limited.")
        return EventTimeline(
            timeline_id=f"timeline:{subject.lower().replace(' ', '_')}",
            subject=subject,
            nodes=nodes,
            links=links,
            headline=headline,
            narrative=narrative,
            confidence=confidence,
            warnings=warnings,
        )

    def build(self, events: Iterable[EventRecord]) -> TimelineBuildResult:
        groups = group_events_by_subject(events)
        timelines = [self.build_for_subject(subject, grouped) for subject, grouped in sorted(groups.items())]
        warnings: List[str] = []
        if not timelines:
            warnings.append("No events supplied to EventTimelineEngine.")
        return TimelineBuildResult(version=self.version, timelines=timelines, warnings=warnings)


def build_event_timelines(events: Iterable[EventRecord]) -> TimelineBuildResult:
    return EventTimelineEngine().build(events)
