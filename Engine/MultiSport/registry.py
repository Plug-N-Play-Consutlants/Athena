"""Canonical sport, league and official connector registries."""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from Engine.MultiSport.models import LeagueProfile, OfficialConnectorProfile, SportEventTaxonomy, SportProfile

COMMON_EVENT_TYPES = [
    "event", "trade", "signing", "injury", "return", "waiver", "claim", "recall", "assignment",
    "suspension", "retirement", "coaching_change", "schedule_change", "game_result", "transaction",
]

SPORT_EVENT_ALIASES: Dict[str, Dict[str, str]] = {
    "nhl": {"goalie_start": "event", "line_change": "event"},
    "nfl": {"inactive": "injury", "roster_move": "transaction", "practice_report": "injury"},
    "nba": {"injury_report": "injury", "two_way_signing": "signing"},
    "mlb": {"il_placement": "injury", "optioned": "assignment", "recalled": "recall"},
    "soccer": {"transfer": "trade", "loan": "transaction", "fixture_change": "schedule_change"},
}


def seed_sport_profiles() -> Dict[str, SportProfile]:
    return {
        "nhl": SportProfile("nhl", "Hockey", "nhl", COMMON_EVENT_TYPES),
        "nfl": SportProfile("nfl", "Football", "nfl", COMMON_EVENT_TYPES),
        "nba": SportProfile("nba", "Basketball", "nba", COMMON_EVENT_TYPES),
        "mlb": SportProfile("mlb", "Baseball", "mlb", COMMON_EVENT_TYPES),
        "soccer": SportProfile("soccer", "Soccer", "uefa", COMMON_EVENT_TYPES),
    }


def seed_league_profiles() -> Dict[str, LeagueProfile]:
    return {
        "nhl": LeagueProfile("nhl", "nhl", "National Hockey League", region="North America", official_source_id="nhl_api"),
        "nfl": LeagueProfile("nfl", "nfl", "National Football League", region="United States", official_source_id="nfl_official"),
        "nba": LeagueProfile("nba", "nba", "National Basketball Association", region="North America", official_source_id="nba_official"),
        "mlb": LeagueProfile("mlb", "mlb", "Major League Baseball", region="North America", official_source_id="mlb_official"),
        "uefa": LeagueProfile("uefa", "soccer", "UEFA Competitions", region="Europe", official_source_id="uefa_official"),
        "fifa": LeagueProfile("fifa", "soccer", "FIFA Competitions", region="global", official_source_id="fifa_official"),
    }


def seed_taxonomies() -> Dict[str, SportEventTaxonomy]:
    return {sport: SportEventTaxonomy(sport, COMMON_EVENT_TYPES, SPORT_EVENT_ALIASES.get(sport, {})) for sport in seed_sport_profiles()}


def seed_official_connector_profiles() -> Dict[str, OfficialConnectorProfile]:
    connectors: Dict[str, OfficialConnectorProfile] = {}
    for league in seed_league_profiles().values():
        connector_id = f"{league.league_id}_official_connector"
        connectors[connector_id] = OfficialConnectorProfile(
            connector_id=connector_id,
            sport_id=league.sport_id,
            league_id=league.league_id,
            source_id=league.official_source_id,
            name=f"{league.name} Official Connector",
            supported_event_types=list(COMMON_EVENT_TYPES),
            network_enabled=False,
            reliability=0.97 if league.league_id == "nhl" else 0.88,
        )
    return connectors


class MultiSportRegistry:
    def __init__(self) -> None:
        self.sports = seed_sport_profiles()
        self.leagues = seed_league_profiles()
        self.taxonomies = seed_taxonomies()
        self.connectors = seed_official_connector_profiles()

    def sport(self, sport_id: str) -> Optional[SportProfile]:
        return self.sports.get((sport_id or "").lower())

    def league(self, league_id: str) -> Optional[LeagueProfile]:
        return self.leagues.get((league_id or "").lower())

    def connectors_for(self, sport_id: str = "", league_id: str = "") -> List[OfficialConnectorProfile]:
        sport_id = (sport_id or "").lower()
        league_id = (league_id or "").lower()
        result: List[OfficialConnectorProfile] = []
        for connector in self.connectors.values():
            if sport_id and connector.sport_id != sport_id:
                continue
            if league_id and connector.league_id != league_id:
                continue
            result.append(connector)
        return sorted(result, key=lambda item: (item.sport_id, item.league_id, item.connector_id))

    def canonical_event_type(self, sport_id: str, event_type: str) -> str:
        taxonomy = self.taxonomies.get((sport_id or "").lower())
        if not taxonomy:
            return "event"
        return taxonomy.canonicalize(event_type)

    def to_dict(self) -> Dict[str, object]:
        return {
            "sports": {key: value.to_dict() for key, value in sorted(self.sports.items())},
            "leagues": {key: value.to_dict() for key, value in sorted(self.leagues.items())},
            "connectors": {key: value.to_dict() for key, value in sorted(self.connectors.items())},
        }


def seed_multi_sport_registry() -> MultiSportRegistry:
    return MultiSportRegistry()
