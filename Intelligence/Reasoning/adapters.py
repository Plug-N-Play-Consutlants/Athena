"""Sport adapter registry for Athena cross-sport reasoning."""
from __future__ import annotations

from typing import Dict, Tuple

from .models import CROSS_SPORT_REASONING_VERSION, ReasoningAdapter


ADAPTERS: Tuple[ReasoningAdapter, ...] = (
    ReasoningAdapter("hockey", ("NHL",), "Hockey Reasoning", {"matchup": "game", "player": "skater or goalie", "club": "team"}),
    ReasoningAdapter("football", ("NFL", "CFL"), "Football Reasoning", {"matchup": "game", "drive": "possession sequence"}),
    ReasoningAdapter("baseball", ("MLB",), "Baseball Reasoning", {"matchup": "game", "series": "multi-game set", "starter": "starting pitcher"}),
    ReasoningAdapter("basketball", ("NBA",), "Basketball Reasoning", {"matchup": "game", "five": "center", "usage": "offensive possession share"}),
    ReasoningAdapter("soccer", ("UEFA", "EPL", "MLS"), "Soccer Reasoning", {"fixture": "match", "club": "team", "transfer": "player movement"}),
)


class ReasoningAdapterRegistry:
    def __init__(self, adapters: Tuple[ReasoningAdapter, ...] | None = None) -> None:
        self._adapters = tuple(adapters or ADAPTERS)
        self._by_sport: Dict[str, ReasoningAdapter] = {adapter.sport.lower(): adapter for adapter in self._adapters}
        self._by_league: Dict[str, ReasoningAdapter] = {
            league.upper(): adapter for adapter in self._adapters for league in adapter.leagues
        }

    def all_adapters(self) -> Tuple[ReasoningAdapter, ...]:
        return self._adapters

    def resolve(self, sport: str = "", league: str = "", intent: str = "general") -> ReasoningAdapter | None:
        league_key = str(league or "").strip().upper()
        sport_key = str(sport or "").strip().lower()
        candidate = self._by_league.get(league_key) if league_key else None
        if candidate and candidate.supports(sport=sport_key, league=league_key, intent=intent):
            return candidate
        candidate = self._by_sport.get(sport_key) if sport_key else None
        if candidate and candidate.supports(sport=sport_key, league=league_key, intent=intent):
            return candidate
        return None

    def stats(self) -> dict:
        return {
            "version": CROSS_SPORT_REASONING_VERSION,
            "adapters": len(self._adapters),
            "sports": sorted(adapter.sport for adapter in self._adapters),
            "leagues": sorted({league for adapter in self._adapters for league in adapter.leagues}),
            "statuses": sorted({adapter.status for adapter in self._adapters}),
        }


def seed_reasoning_adapter_registry() -> ReasoningAdapterRegistry:
    return ReasoningAdapterRegistry()


def adapter_registry_diagnostics() -> dict:
    registry = seed_reasoning_adapter_registry()
    stats = registry.stats()
    return {
        "panel": "reasoning_adapters",
        "status": "pass" if stats["adapters"] >= 5 else "warn",
        "version": CROSS_SPORT_REASONING_VERSION,
        "stats": stats,
        "adapters": [adapter.to_dict() for adapter in registry.all_adapters()],
    }


__all__ = [
    "ADAPTERS",
    "ReasoningAdapterRegistry",
    "seed_reasoning_adapter_registry",
    "adapter_registry_diagnostics",
]
