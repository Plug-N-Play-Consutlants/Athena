"""Source intelligence registry for Event Intelligence.

Source profiles are capability metadata, not subscription tiers. They tell Athena
how much evidentiary weight a normalized event should receive.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from Knowledge.Events.models import EventSourceProfile

SOURCE_INTELLIGENCE_VERSION = "0.5.1.5.0"


@dataclass
class SourceRegistry:
    sources: Dict[str, EventSourceProfile] = field(default_factory=dict)

    def register(self, profile: EventSourceProfile) -> EventSourceProfile:
        if not profile.source_id:
            raise ValueError("source_id is required")
        self.sources[profile.source_id] = profile
        return profile

    def get(self, source_id: str) -> Optional[EventSourceProfile]:
        return self.sources.get(source_id)

    def primary_fact_sources(self) -> List[EventSourceProfile]:
        return [source for source in self.sources.values() if source.is_primary_fact_source()]

    def by_type(self, *source_types: str) -> List[EventSourceProfile]:
        allowed = set(source_types)
        return [source for source in self.sources.values() if source.source_type in allowed]

    def to_dict(self) -> Dict[str, object]:
        return {
            "version": SOURCE_INTELLIGENCE_VERSION,
            "source_count": len(self.sources),
            "primary_fact_source_count": len(self.primary_fact_sources()),
            "sources": {key: value.to_dict() for key, value in sorted(self.sources.items())},
        }


def seed_source_registry() -> SourceRegistry:
    registry = SourceRegistry()
    profiles = [
        EventSourceProfile("nhl_api", "NHL Official API", "official_api", sport="nhl", league="nhl", authority="official", reliability=0.98, freshness=0.95, confidence_modifier=0.03, access_method="api", notes="Preferred NHL structured source."),
        EventSourceProfile("league_feed", "Official League Feed", "official_feed", authority="official", reliability=0.95, freshness=0.92, confidence_modifier=0.02, access_method="feed", notes="Generic official league event source profile."),
        EventSourceProfile("transaction_feed", "Structured Transaction Feed", "structured_feed", authority="trusted", reliability=0.9, freshness=0.88, access_method="feed", notes="Provider-neutral transaction feed contract."),
        EventSourceProfile("trusted_newswire", "Trusted Newswire", "newswire", authority="trusted", reliability=0.85, freshness=0.82, access_method="rss", notes="AP/Reuters-style corroboration source profile."),
        EventSourceProfile("team_official", "Official Team Source", "official_team", authority="official", reliability=0.88, freshness=0.86, access_method="site_or_feed", notes="Useful for injuries, signings, recalls and lineup updates."),
        EventSourceProfile("fantasy_provider", "Fantasy Provider Feed", "provider_feed", authority="trusted", reliability=0.78, freshness=0.9, access_method="provider", notes="Provider enrichment source; supplements general intelligence."),
        EventSourceProfile("opinion_article", "Opinion Article", "article", authority="low", reliability=0.35, freshness=0.5, opinion_weight=0.85, access_method="web", notes="Deprioritized by design; may explain discourse but should not own facts."),
    ]
    for profile in profiles:
        registry.register(profile)
    return registry


def source_profile_for(source_id: str, registry: SourceRegistry | None = None) -> EventSourceProfile:
    active = registry or seed_source_registry()
    return active.get(source_id) or EventSourceProfile(source_id or "unknown", source_id or "Unknown Source", "unknown", authority="unknown", reliability=0.45, freshness=0.5, opinion_weight=0.5)


def score_source_confidence(source_id: str, base_confidence: float = 0.65, registry: SourceRegistry | None = None) -> float:
    profile = source_profile_for(source_id, registry)
    score = (float(base_confidence) * 0.55) + (profile.trust_score * 0.45)
    return max(0.0, min(1.0, score))


def source_registry_summary() -> Dict[str, object]:
    registry = seed_source_registry()
    return {
        **registry.to_dict(),
        "preferred_source_types": ["official_api", "official_feed", "structured_feed", "newswire", "official_team", "provider_feed"],
        "opinion_sources_deprioritized": True,
    }
