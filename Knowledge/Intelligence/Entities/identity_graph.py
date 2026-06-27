"""Public identity graph seed helpers for PIF-1 Build 002."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .entity_registry import PublicEntity, all_entities, registry_stats


@dataclass(frozen=True)
class IdentityGraphSummary:
    entity_count: int
    player_count: int
    team_count: int
    alias_count: int
    ambiguous_names: Dict[str, int] = field(default_factory=dict)
    public_guardrails: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "entity_count": self.entity_count,
            "player_count": self.player_count,
            "team_count": self.team_count,
            "alias_count": self.alias_count,
            "ambiguous_names": dict(self.ambiguous_names),
            "public_guardrails": list(self.public_guardrails),
        }


def graph_summary() -> IdentityGraphSummary:
    stats = registry_stats()
    by_type = stats.get("by_type", {}) or {}
    return IdentityGraphSummary(
        entity_count=int(stats.get("entities", 0)),
        player_count=int(by_type.get("player", 0)),
        team_count=int(by_type.get("team", 0)),
        alias_count=int(stats.get("aliases", 0)),
        ambiguous_names=dict(stats.get("ambiguous_names", {}) or {}),
        public_guardrails=[
            "Public questions resolve against the public entity registry before fantasy data.",
            "Ambiguous duplicate-name entities require clarification.",
            "Fantasy context is an optional lens, not the default public comparison route.",
            "Rulebook knowledge is only eligible for rulebook/CBA intents.",
        ],
    )


def entity_profile(entity: PublicEntity) -> Dict[str, object]:
    data = entity.to_dict()
    data["identity_complete"] = bool(entity.canonical_name and entity.entity_type and entity.league)
    data["has_public_summary"] = bool(entity.summary)
    data["has_draft_context"] = bool(entity.draft)
    return data
