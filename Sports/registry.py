"""Sport registry for Athena Multi-Sport Intelligence Foundation.

The registry is provider-neutral and deterministic. It defines sport metadata used
by routing, intelligence capability discovery, and Studio diagnostics without
coupling Athena to a specific upstream provider.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Iterable, Tuple

SPORT_REGISTRY_VERSION = "0.5.5.0.0"


@dataclass(frozen=True)
class SportDefinition:
    sport_id: str
    display_name: str
    primary_leagues: Tuple[str, ...]
    positions: Tuple[str, ...]
    season_model: str
    schedule_unit: str
    statistics: Tuple[str, ...]
    event_taxonomy: Tuple[str, ...]
    terminology: Dict[str, str] = field(default_factory=dict)
    status: str = "active"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["provider_neutral"] = True
        return data


SPORT_DEFINITIONS: Tuple[SportDefinition, ...] = (
    SportDefinition(
        sport_id="hockey",
        display_name="Hockey",
        primary_leagues=("NHL",),
        positions=("C", "LW", "RW", "D", "G"),
        season_model="fall_to_spring",
        schedule_unit="game",
        statistics=("goals", "assists", "points", "shots", "toi", "power_play_points", "saves", "goals_against"),
        event_taxonomy=("injury", "transaction", "lineup", "trade", "contract", "schedule", "game_result"),
        terminology={"club": "team", "fixture": "game", "skater": "non-goalie player"},
    ),
    SportDefinition(
        sport_id="football",
        display_name="Football",
        primary_leagues=("NFL", "CFL"),
        positions=("QB", "RB", "WR", "TE", "OL", "DL", "LB", "CB", "S", "K"),
        season_model="fall_to_winter",
        schedule_unit="game",
        statistics=("passing_yards", "rushing_yards", "receiving_yards", "touchdowns", "tackles", "sacks", "interceptions"),
        event_taxonomy=("injury", "depth_chart", "transaction", "trade", "contract", "schedule", "game_result"),
        terminology={"matchup": "game", "drive": "possession sequence"},
    ),
    SportDefinition(
        sport_id="baseball",
        display_name="Baseball",
        primary_leagues=("MLB",),
        positions=("SP", "RP", "C", "1B", "2B", "3B", "SS", "OF", "DH"),
        season_model="spring_to_fall",
        schedule_unit="game",
        statistics=("runs", "home_runs", "rbi", "ops", "era", "whip", "strikeouts", "innings_pitched"),
        event_taxonomy=("injury", "lineup", "rotation", "transaction", "trade", "contract", "schedule", "game_result"),
        terminology={"series": "multi-game set", "starter": "starting pitcher"},
    ),
    SportDefinition(
        sport_id="basketball",
        display_name="Basketball",
        primary_leagues=("NBA",),
        positions=("PG", "SG", "SF", "PF", "C"),
        season_model="fall_to_summer",
        schedule_unit="game",
        statistics=("points", "rebounds", "assists", "steals", "blocks", "minutes", "usage_rate"),
        event_taxonomy=("injury", "lineup", "rotation", "transaction", "trade", "contract", "schedule", "game_result"),
        terminology={"five": "center", "usage": "offensive possession share"},
    ),
    SportDefinition(
        sport_id="soccer",
        display_name="Soccer",
        primary_leagues=("UEFA", "EPL", "MLS"),
        positions=("GK", "DEF", "MID", "FWD", "WB", "DM", "AM"),
        season_model="league_specific",
        schedule_unit="match",
        statistics=("goals", "assists", "xg", "xa", "shots", "key_passes", "clean_sheets", "saves"),
        event_taxonomy=("injury", "lineup", "transfer", "contract", "schedule", "match_result", "suspension"),
        terminology={"fixture": "match", "club": "team", "transfer": "player movement"},
    ),
)


class SportRegistry:
    def __init__(self, definitions: Iterable[SportDefinition] | None = None) -> None:
        self._definitions: Tuple[SportDefinition, ...] = tuple(definitions or SPORT_DEFINITIONS)
        self._by_id = {item.sport_id.lower(): item for item in self._definitions}
        self._by_league = {league.lower(): item for item in self._definitions for league in item.primary_leagues}

    def all_sports(self) -> Tuple[SportDefinition, ...]:
        return self._definitions

    def get(self, sport_id: str) -> SportDefinition | None:
        return self._by_id.get(str(sport_id or "").strip().lower())

    def for_league(self, league: str) -> SportDefinition | None:
        return self._by_league.get(str(league or "").strip().lower())

    def stats(self) -> Dict[str, Any]:
        return {
            "version": SPORT_REGISTRY_VERSION,
            "sports": len(self._definitions),
            "sport_ids": sorted(item.sport_id for item in self._definitions),
            "leagues": sorted({league for item in self._definitions for league in item.primary_leagues}),
            "positions": sum(len(item.positions) for item in self._definitions),
            "event_types": sorted({event for item in self._definitions for event in item.event_taxonomy}),
            "provider_neutral": True,
        }


def seed_sport_registry() -> SportRegistry:
    return SportRegistry()


def sport_registry_diagnostics(registry: SportRegistry | None = None) -> Dict[str, Any]:
    registry = registry or seed_sport_registry()
    stats = registry.stats()
    return {
        "panel": "sport_registry",
        "status": "pass" if stats["sports"] >= 5 else "warn",
        "version": SPORT_REGISTRY_VERSION,
        "stats": stats,
        "sports": [sport.to_dict() for sport in registry.all_sports()],
    }


__all__ = [
    "SPORT_REGISTRY_VERSION",
    "SportDefinition",
    "SportRegistry",
    "seed_sport_registry",
    "sport_registry_diagnostics",
]
