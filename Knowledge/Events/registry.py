"""Event and source registry for Athena Event Intelligence.

Knowledge owns event taxonomy and source trust profiles. This module preserves
backward-compatible exports used by Event Intelligence engines across Epic 5.
"""
from __future__ import annotations

from typing import Dict, List

from Knowledge.Events.models import EventRegistry, EventSourceProfile

EVENT_INTELLIGENCE_VERSION = "0.5.3.1.2"

EVENT_TYPES = [
    "event",
    "transaction",
    "trade",
    "free_agent_signing",
    "signing",
    "contract_extension",
    "extension",
    "release",
    "waiver",
    "claim",
    "recall",
    "assignment",
    "call_up",
    "send_down",
    "demotion",
    "injury",
    "return",
    "suspension",
    "retirement",
    "coaching_change",
    "lineup_change",
    "schedule_change",
    "game_result",
    "official_rule_update",
]

EVENT_TYPE_ALIASES = {
    "": "event",
    "waivers": "waiver",
    "waiver_claim": "claim",
    "claimed": "claim",
    "fa_signing": "free_agent_signing",
    "free agency": "free_agent_signing",
    "free_agent": "free_agent_signing",
    "signed": "free_agent_signing",
    "signing": "free_agent_signing",
    "extension": "contract_extension",
    "contract_extension": "contract_extension",
    "called_up": "call_up",
    "callup": "call_up",
    "recall": "call_up",
    "assigned": "assignment",
    "assignment": "assignment",
    "sent_down": "send_down",
    "senddown": "send_down",
    "demotion": "send_down",
    "injured": "injury",
    "activated": "return",
    "return_from_injury": "return",
    "coach_change": "coaching_change",
    "coaching": "coaching_change",
    "schedule": "schedule_change",
    "score": "game_result",
    "game": "game_result",
    "result": "game_result",
}


def canonical_event_types() -> List[str]:
    """Return Athena's canonical event taxonomy.

    This compatibility export is intentionally stable. Several Epic 5 engines
    import it through ``Knowledge.Events`` and ``Knowledge.Events.registry``.
    """
    return list(EVENT_TYPES)


def canonical_event_type(event_type: str) -> str:
    """Normalize a provider/source event type into Athena's taxonomy."""
    raw = str(event_type or "event").strip().lower().replace("-", "_").replace(" ", "_")
    canonical = EVENT_TYPE_ALIASES.get(raw, raw)
    return canonical if canonical in EVENT_TYPES else "event"


def seed_event_registry() -> EventRegistry:
    registry = EventRegistry()
    source_profiles = [
        EventSourceProfile("nhl_api", "NHL Official API", "official_api", sport="nhl", league="nhl", authority="official", reliability=0.98, freshness=0.95, confidence_modifier=0.03, access_method="api", notes="Preferred NHL structured source."),
        EventSourceProfile("nfl_api", "NFL Official Source", "official_api", sport="football", league="nfl", authority="official", reliability=0.94, freshness=0.90, confidence_modifier=0.02, access_method="api", notes="Official NFL structured source profile."),
        EventSourceProfile("nba_api", "NBA Official Source", "official_api", sport="basketball", league="nba", authority="official", reliability=0.94, freshness=0.90, confidence_modifier=0.02, access_method="api", notes="Official NBA structured source profile."),
        EventSourceProfile("mlb_api", "MLB Official Source", "official_api", sport="baseball", league="mlb", authority="official", reliability=0.94, freshness=0.90, confidence_modifier=0.02, access_method="api", notes="Official MLB structured source profile."),
        EventSourceProfile("soccer_official", "Official Soccer Source", "official_feed", sport="soccer", league="multi", authority="official", reliability=0.90, freshness=0.88, confidence_modifier=0.01, access_method="feed", notes="Official soccer competition source profile."),
        EventSourceProfile("league_feed", "Official League Feed", "official_feed", authority="official", reliability=0.95, freshness=0.92, confidence_modifier=0.02, access_method="feed", notes="Generic official league event source profile."),
        EventSourceProfile("transaction_feed", "Structured Transaction Feed", "structured_feed", authority="trusted", reliability=0.90, freshness=0.88, access_method="feed", notes="Provider-neutral transaction feed contract."),
        EventSourceProfile("trusted_newswire", "Trusted Newswire", "newswire", authority="trusted", reliability=0.85, freshness=0.82, access_method="rss", notes="AP/Reuters-style corroboration source profile."),
        EventSourceProfile("team_official", "Official Team Source", "official_team", authority="official", reliability=0.88, freshness=0.86, access_method="site_or_feed", notes="Useful for injuries, signings, recalls and lineup updates."),
        EventSourceProfile("fantasy_provider", "Fantasy Provider Feed", "provider_feed", authority="trusted", reliability=0.78, freshness=0.90, access_method="provider", notes="Provider enrichment source; supplements general intelligence."),
        EventSourceProfile("provider_fantasy", "Fantasy Provider Feed", "provider_feed", authority="trusted", reliability=0.78, freshness=0.90, access_method="provider", notes="Backward-compatible fantasy provider source id."),
        EventSourceProfile("opinion_article", "Opinion Article", "article", authority="low", reliability=0.35, freshness=0.50, opinion_weight=0.85, access_method="web", notes="Deprioritized by design; may explain discourse but should not own facts."),
    ]
    for profile in source_profiles:
        registry.register_source(profile)
    return registry


def source_registry_summary() -> Dict[str, object]:
    registry = seed_event_registry()
    return {
        "version": EVENT_INTELLIGENCE_VERSION,
        "source_count": registry.source_count(),
        "trusted_source_count": len(registry.trusted_sources()),
        "event_types": canonical_event_types(),
        "preferred_source_types": ["official_api", "official_feed", "structured_feed", "newswire", "official_team", "provider_feed"],
        "opinion_sources_deprioritized": True,
    }
