"""Event Summarization Engine for Athena 0.5.2.5.0.

This engine turns normalized event facts, timeline reasoning and confidence
metadata into concise Scout-ready intelligence. It does not fetch external data
and does not mutate Knowledge; it composes outputs produced by prior Event
Intelligence engines.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from Engine.EventConfidence.confidence_engine import EventConfidenceEngine
from Engine.EventConfidence.confidence_models import EventConfidenceResult, SourceCorroborationResult
from Engine.EventReasoning.reasoning_engine import EventReasoningEngine
from Engine.EventReasoning.models import EventReasoningBatch, EventReasoningResult
from Engine.EventTimeline.timeline_builder import EventTimelineEngine
from Engine.EventTimeline.timeline_models import EventTimeline, TimelineBuildResult
from Knowledge.Events.models import EventRecord
from Engine.EventSummarization.summary_models import EventExecutiveBrief, EventSummaryBatch, EventSummaryItem

EVENT_SUMMARIZATION_ENGINE_VERSION = "0.5.2.5.0"


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}:" + hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def _event_sort_key(event: EventRecord) -> tuple[str, str]:
    return (event.occurred_at or "", event.event_id)


def _headline_for(event: EventRecord) -> str:
    etype = (event.event_type or "event").replace("_", " ").title()
    subject = event.subject or "Unknown subject"
    return f"{subject}: {etype}"


def _confidence_by_event(confidence: Optional[SourceCorroborationResult]) -> Dict[str, EventConfidenceResult]:
    if not confidence:
        return {}
    return {item.event_id: item for item in confidence.results}


def _reasoning_by_event(reasoning: Optional[EventReasoningBatch]) -> Dict[str, EventReasoningResult]:
    if not reasoning:
        return {}
    return {item.event_id: item for item in reasoning.results}


def _timeline_text(timelines: Sequence[EventTimeline]) -> str:
    if not timelines:
        return "No event timeline was available."
    primary = sorted(timelines, key=lambda item: (-item.event_count, item.subject))[0]
    if primary.narrative:
        return primary.narrative
    return f"{primary.subject} has {primary.event_count} related event(s) in the current timeline."


class EventSummarizationEngine:
    """Compose event summaries, executive briefs and Scout payloads."""

    version = EVENT_SUMMARIZATION_ENGINE_VERSION

    def summarize_events(
        self,
        events: Iterable[EventRecord],
        *,
        reasoning: Optional[EventReasoningBatch] = None,
        timelines: Optional[TimelineBuildResult] = None,
        confidence: Optional[SourceCorroborationResult] = None,
        title: str = "Event Intelligence Summary",
    ) -> EventSummaryBatch:
        event_list = sorted(list(events), key=_event_sort_key)
        warnings: List[str] = []
        if reasoning is None:
            reasoning = EventReasoningEngine().reason_about_events(event_list)
            warnings.append("Reasoning was generated inside EventSummarizationEngine.")
        if confidence is None:
            confidence = EventConfidenceEngine().score_events(event_list)
            warnings.append("Confidence was generated inside EventSummarizationEngine.")
        if timelines is None:
            timelines = EventTimelineEngine().build(event_list)
            warnings.append("Timeline was generated inside EventSummarizationEngine.")

        conf_map = _confidence_by_event(confidence)
        reason_map = _reasoning_by_event(reasoning)
        items: List[EventSummaryItem] = []
        seen_signatures: set[str] = set()
        for event in event_list:
            signature = "|".join([event.event_type, event.subject.lower(), event.summary.lower()])
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)
            conf = conf_map.get(event.event_id)
            reas = reason_map.get(event.event_id)
            confidence_score = conf.score if conf else int(round(max(0.0, min(1.0, event.confidence or 0.55)) * 100))
            confidence_label = conf.label if conf else "developing"
            significance = reas.impact.significance if reas else "moderate"
            reasoning_text = reas.executive_summary if reas else event.summary
            items.append(EventSummaryItem(
                event_id=event.event_id,
                subject=event.subject,
                event_type=event.event_type,
                headline=_headline_for(event),
                summary=event.summary,
                occurred_at=event.occurred_at,
                confidence_label=confidence_label,
                confidence_score=confidence_score,
                significance=significance,
                source_ids=list(event.source_ids),
                reasoning=reasoning_text,
            ))

        executive = self._executive_summary(items)
        what_changed = self._what_changed(items)
        confidence_summary = self._confidence_summary(items, confidence)
        timeline_summary = _timeline_text(timelines.timelines if timelines else [])
        brief = EventExecutiveBrief(
            brief_id=_stable_id("event_brief", title + "|" + "|".join(item.event_id for item in items)),
            title=title,
            executive_summary=executive,
            what_changed=what_changed,
            confidence_summary=confidence_summary,
            timeline_summary=timeline_summary,
            items=items,
            warnings=warnings,
        )
        return EventSummaryBatch(version=self.version, brief=brief, scout_payload=self.scout_payload(brief))

    def _executive_summary(self, items: Sequence[EventSummaryItem]) -> str:
        if not items:
            return "No events were available to summarize."
        high = [item for item in items if item.significance in {"high", "major"}]
        confirmed = [item for item in items if item.confidence_label in {"confirmed", "strong"}]
        type_counts = Counter(item.event_type for item in items)
        primary_type = type_counts.most_common(1)[0][0].replace("_", " ") if type_counts else "event"
        lead = high[0] if high else items[-1]
        return (
            f"Athena summarized {len(items)} event(s). The leading item is {lead.headline}, "
            f"with {lead.confidence_label} confidence and {lead.significance} significance. "
            f"The current event mix is led by {primary_type} activity; {len(confirmed)} item(s) have strong or confirmed support."
        )

    def _what_changed(self, items: Sequence[EventSummaryItem]) -> str:
        if not items:
            return "Nothing changed in the supplied event set."
        newest = items[-1]
        return f"Latest change: {newest.summary} This affects {newest.subject} and is categorized as {newest.event_type.replace('_', ' ')}."

    def _confidence_summary(self, items: Sequence[EventSummaryItem], confidence: Optional[SourceCorroborationResult]) -> str:
        if not items:
            return "No confidence assessment was available."
        avg = round(sum(item.confidence_score for item in items) / max(1, len(items)))
        conflicts = confidence.conflict_count if confidence else 0
        corroborated = confidence.corroborated_count if confidence else sum(1 for item in items if item.confidence_label in {"confirmed", "strong"})
        if conflicts:
            return f"Average confidence is {avg}/100 with {conflicts} conflict group(s); Athena should present this as developing until resolved."
        return f"Average confidence is {avg}/100 with {corroborated} corroborated or high-confidence item(s)."

    def scout_payload(self, brief: EventExecutiveBrief) -> Dict[str, object]:
        return {
            "renderer": "event_summary",
            "title": brief.title,
            "executive_summary": brief.executive_summary,
            "what_changed": brief.what_changed,
            "confidence_summary": brief.confidence_summary,
            "timeline_summary": brief.timeline_summary,
            "items": [item.to_dict() for item in brief.items],
            "warnings": list(brief.warnings),
        }


def summarize_events(events: Iterable[EventRecord], **kwargs: object) -> EventSummaryBatch:
    return EventSummarizationEngine().summarize_events(events, **kwargs)  # type: ignore[arg-type]


def scout_event_summary_payload(batch: EventSummaryBatch) -> Dict[str, object]:
    return dict(batch.scout_payload)
