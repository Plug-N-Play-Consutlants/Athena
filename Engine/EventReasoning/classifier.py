"""Deterministic event classification utilities."""
from __future__ import annotations

from typing import Iterable, List

HIGH_IMPACT_TYPES = {"trade", "injury", "signing", "extension", "suspension", "coaching_change"}
MEDIUM_IMPACT_TYPES = {"waiver", "claim", "recall", "assignment", "return", "schedule_change", "game_result", "transaction"}
PLAYER_DOMAIN_TYPES = {"trade", "injury", "signing", "extension", "waiver", "claim", "recall", "assignment", "return", "suspension", "retirement"}
TEAM_DOMAIN_TYPES = {"trade", "signing", "extension", "coaching_change", "game_result", "schedule_change", "transaction"}
FANTASY_DOMAIN_TYPES = {"trade", "injury", "signing", "waiver", "claim", "recall", "assignment", "return", "suspension", "schedule_change"}


def normalized_type(event_type: str | None) -> str:
    return (event_type or "event").strip().lower().replace(" ", "_").replace("-", "_")


def significance_for(event_type: str | None, confidence: float = 0.65) -> str:
    etype = normalized_type(event_type)
    if etype in HIGH_IMPACT_TYPES and confidence >= 0.82:
        return "major"
    if etype in HIGH_IMPACT_TYPES:
        return "high"
    if etype in MEDIUM_IMPACT_TYPES:
        return "moderate"
    return "low"


def affected_domains_for(event_type: str | None) -> List[str]:
    etype = normalized_type(event_type)
    domains: List[str] = ["events"]
    if etype in PLAYER_DOMAIN_TYPES:
        domains.append("player")
    if etype in TEAM_DOMAIN_TYPES:
        domains.append("team")
    if etype in FANTASY_DOMAIN_TYPES:
        domains.append("fantasy")
    if etype in {"trade", "signing", "extension", "coaching_change"}:
        domains.append("organization")
    if etype in {"schedule_change", "game_result"}:
        domains.append("schedule")
    return domains
