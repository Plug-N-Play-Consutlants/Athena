"""Source confidence profiles for Athena Event Intelligence."""
from __future__ import annotations

from typing import Dict, Iterable

from Engine.EventConfidence.confidence_models import SourceConfidenceProfile
from Knowledge.Events.models import EventSourceProfile

OFFICIAL_SOURCE_IDS = {"nhl_api", "official_nhl", "nhl_schedule", "nhl_scores", "league_official"}
WIRE_SOURCE_IDS = {"associated_press", "ap", "reuters", "trusted_newswire"}
TRUSTED_NEWS_IDS = {"tsn", "sportsnet", "cbs_sports", "cbc_sports"}
RUMOUR_SOURCE_IDS = {"rumour_blog", "social_media", "unverified_report"}


def profile_for_source(source_id: str, registry_profile: EventSourceProfile | None = None) -> SourceConfidenceProfile:
    """Return a deterministic confidence profile for a source identifier."""

    normalized = (source_id or "unknown").lower()
    if registry_profile is not None:
        return SourceConfidenceProfile(
            source_id=registry_profile.source_id,
            display_name=registry_profile.display_name,
            authority=registry_profile.authority,
            reliability=registry_profile.reliability,
            timeliness=registry_profile.freshness,
            completeness=max(0.5, 1.0 - registry_profile.opinion_weight),
            availability=0.8,
            opinion_weight=registry_profile.opinion_weight,
            corroboration_weight=registry_profile.trust_score,
        )
    if normalized in OFFICIAL_SOURCE_IDS or normalized.startswith("official"):
        return SourceConfidenceProfile(source_id=source_id, display_name=source_id, authority="official", reliability=0.96, timeliness=0.92, completeness=0.92, availability=0.9, corroboration_weight=1.0)
    if normalized in WIRE_SOURCE_IDS:
        return SourceConfidenceProfile(source_id=source_id, display_name=source_id, authority="wire", reliability=0.90, timeliness=0.88, completeness=0.86, availability=0.88, corroboration_weight=0.94)
    if normalized in TRUSTED_NEWS_IDS:
        return SourceConfidenceProfile(source_id=source_id, display_name=source_id, authority="trusted", reliability=0.84, timeliness=0.82, completeness=0.80, availability=0.84, corroboration_weight=0.86)
    if normalized in RUMOUR_SOURCE_IDS or "rumour" in normalized or "rumor" in normalized:
        return SourceConfidenceProfile(source_id=source_id, display_name=source_id, authority="unverified", reliability=0.35, timeliness=0.75, completeness=0.35, availability=0.70, opinion_weight=0.8, corroboration_weight=0.35)
    return SourceConfidenceProfile(source_id=source_id, display_name=source_id)


def source_profile_registry(source_ids: Iterable[str]) -> Dict[str, SourceConfidenceProfile]:
    return {source_id: profile_for_source(source_id) for source_id in sorted(set(source_ids)) if source_id}


def confidence_profile_summary(profiles: Iterable[SourceConfidenceProfile]) -> dict:
    items = list(profiles)
    return {
        "source_count": len(items),
        "official_count": sum(1 for item in items if item.authority == "official"),
        "trusted_count": sum(1 for item in items if item.trust_score >= 0.75),
        "average_trust": round(sum(item.trust_score for item in items) / max(1, len(items)), 3),
    }
