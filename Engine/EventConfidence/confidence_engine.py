"""Event Confidence & Source Corroboration engine for Athena 0.5.2.4.0."""
from __future__ import annotations

from typing import Dict, Iterable, List, Sequence

from Engine.EventConfidence.confidence_models import ConfidenceExplanation, EventConfidenceResult, SourceCorroborationResult, SourceConfidenceProfile
from Engine.EventConfidence.corroboration import build_corroboration_timeline, detect_conflicting_events, group_events_for_corroboration, source_ids_for_event
from Engine.EventConfidence.source_profiles import profile_for_source, source_profile_registry
from Knowledge.Events.evidence_fusion import event_signature
from Knowledge.Events.models import EventRecord

EVENT_CONFIDENCE_ENGINE_VERSION = "0.5.2.4.0"


def confidence_label(score: int) -> str:
    if score >= 88:
        return "confirmed"
    if score >= 74:
        return "strong"
    if score >= 58:
        return "developing"
    if score >= 40:
        return "weak"
    return "unverified"


class EventConfidenceEngine:
    """Scores event confidence using source quality, corroboration and conflict signals."""

    version = EVENT_CONFIDENCE_ENGINE_VERSION

    def __init__(self, source_profiles: Dict[str, SourceConfidenceProfile] | None = None) -> None:
        self.source_profiles = source_profiles or {}

    def profile(self, source_id: str) -> SourceConfidenceProfile:
        return self.source_profiles.get(source_id) or profile_for_source(source_id)

    def _score_bucket(self, bucket: Sequence[EventRecord], conflict_event_ids: set[str]) -> EventConfidenceResult:
        canonical = sorted(bucket, key=lambda event: (-(event.confidence or 0), event.event_id))[0]
        source_ids = sorted({source_id for event in bucket for source_id in source_ids_for_event(event)}) or ["unknown"]
        profiles = [self.profile(source_id) for source_id in source_ids]
        trust_component = sum(profile.trust_score for profile in profiles) / max(1, len(profiles))
        event_component = sum(max(0.0, min(1.0, event.confidence or 0.65)) for event in bucket) / max(1, len(bucket))
        corroboration_bonus = min(0.18, max(0, len(source_ids) - 1) * 0.06)
        official_bonus = 0.06 if any(profile.authority == "official" for profile in profiles) else 0.0
        conflict_penalty = 0.20 if any(event.event_id in conflict_event_ids for event in bucket) else 0.0
        score_float = (trust_component * 0.45) + (event_component * 0.35) + corroboration_bonus + official_bonus - conflict_penalty
        score = int(round(max(0.0, min(1.0, score_float)) * 100))
        label = confidence_label(score)
        bucket_conflicted = any(event.event_id in conflict_event_ids for event in bucket)
        supporting = [] if bucket_conflicted else list(source_ids)
        conflicting = list(source_ids) if bucket_conflicted else []
        factors = [
            f"{len(source_ids)} source{'s' if len(source_ids) != 1 else ''} observed this event",
            f"average source trust {trust_component:.2f}",
            f"event confidence average {event_component:.2f}",
        ]
        if official_bonus:
            factors.append("official source present")
        if corroboration_bonus:
            factors.append("cross-source corroboration present")
        warnings: List[str] = []
        if conflict_penalty:
            warnings.append("conflicting source evidence detected")
        if len(source_ids) == 1:
            warnings.append("single-source event; confidence is capped by source quality")
        summary = f"{canonical.subject} {canonical.event_type} confidence is {label} ({score}/100)."
        explanation = ConfidenceExplanation(label=label, score=score, summary=summary, factors=factors, warnings=warnings)
        return EventConfidenceResult(
            event_id=canonical.event_id,
            subject=canonical.subject,
            event_type=canonical.event_type,
            score=score,
            label=label,
            source_ids=source_ids,
            supporting_sources=supporting,
            conflicting_sources=conflicting,
            corroborated=len(source_ids) > 1,
            conflict_detected=bool(conflicting),
            explanation=explanation,
        )

    def score_events(self, events: Iterable[EventRecord]) -> SourceCorroborationResult:
        event_list = list(events)
        buckets = group_events_for_corroboration(event_list)
        conflicts = detect_conflicting_events(event_list)
        conflict_event_ids = {
            event.event_id
            for bucket in conflicts.values()
            for event in bucket
        }
        results = [self._score_bucket(bucket, conflict_event_ids) for _, bucket in sorted(buckets.items())]
        warnings: List[str] = []
        if not event_list:
            warnings.append("No events supplied to EventConfidenceEngine.")
        if conflicts:
            warnings.append(f"{len(conflicts)} potential source conflict group(s) detected.")
        return SourceCorroborationResult(
            version=self.version,
            results=results,
            timeline=build_corroboration_timeline(event_list),
            warnings=warnings,
        )

    def explain_event(self, event: EventRecord) -> ConfidenceExplanation:
        result = self.score_events([event])
        if not result.results:
            return ConfidenceExplanation(label="unknown", score=0, summary="No event confidence could be computed.", warnings=["No event supplied"])
        return result.results[0].explanation or ConfidenceExplanation(label=result.results[0].label, score=result.results[0].score, summary="Confidence computed.")


def score_event_confidence(events: Iterable[EventRecord], profiles: Dict[str, SourceConfidenceProfile] | None = None) -> SourceCorroborationResult:
    return EventConfidenceEngine(profiles).score_events(events)


def scout_confidence_payload(result: EventConfidenceResult) -> dict:
    explanation = result.explanation.to_dict() if result.explanation else {}
    return {
        "event_id": result.event_id,
        "confidence_label": result.label,
        "confidence_score": result.score,
        "corroborated": result.corroborated,
        "conflict_detected": result.conflict_detected,
        "summary": explanation.get("summary", ""),
        "factors": explanation.get("factors", []),
        "warnings": explanation.get("warnings", []),
    }
