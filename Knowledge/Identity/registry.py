"""Seeded cross-sport identity registry for Athena v0.5.3.2.0."""
from __future__ import annotations

from typing import Dict, Iterable, List, Sequence

from .models import ExternalIdentifier, IdentityEntity, normalized_key


def _ids(*pairs: tuple[str, str, float] | tuple[str, str]) -> tuple[ExternalIdentifier, ...]:
    out: list[ExternalIdentifier] = []
    for pair in pairs:
        if len(pair) == 2:
            namespace, value = pair  # type: ignore[misc]
            confidence = 1.0
        else:
            namespace, value, confidence = pair  # type: ignore[misc]
        out.append(ExternalIdentifier(namespace, value, float(confidence)))
    return tuple(out)


SEED_IDENTITY_ENTITIES: tuple[IdentityEntity, ...] = (
    IdentityEntity("sport.hockey", "sport", "Hockey", "hockey", "global", aliases=("ice hockey",)),
    IdentityEntity("sport.football", "sport", "Football", "football", "global", aliases=("american football",)),
    IdentityEntity("sport.basketball", "sport", "Basketball", "basketball", "global"),
    IdentityEntity("sport.baseball", "sport", "Baseball", "baseball", "global"),
    IdentityEntity("sport.soccer", "sport", "Soccer", "soccer", "global", aliases=("football", "association football")),
    IdentityEntity("league.nhl", "league", "National Hockey League", "hockey", "NHL", aliases=("NHL",), external_ids=_ids(("league", "nhl"))),
    IdentityEntity("league.nfl", "league", "National Football League", "football", "NFL", aliases=("NFL",), external_ids=_ids(("league", "nfl"))),
    IdentityEntity("league.nba", "league", "National Basketball Association", "basketball", "NBA", aliases=("NBA",), external_ids=_ids(("league", "nba"))),
    IdentityEntity("league.mlb", "league", "Major League Baseball", "baseball", "MLB", aliases=("MLB",), external_ids=_ids(("league", "mlb"))),
    IdentityEntity("league.uefa", "league", "UEFA", "soccer", "UEFA", aliases=("Union of European Football Associations",), external_ids=_ids(("league", "uefa"))),
    IdentityEntity("nhl.team.tor", "team", "Toronto Maple Leafs", "hockey", "NHL", aliases=("Leafs", "Maple Leafs", "Toronto", "TOR"), external_ids=_ids(("nhl:team", "TOR"))),
    IdentityEntity("nhl.team.edm", "team", "Edmonton Oilers", "hockey", "NHL", aliases=("Oilers", "Edmonton", "EDM"), external_ids=_ids(("nhl:team", "EDM"))),
    IdentityEntity("nhl.team.car", "team", "Carolina Hurricanes", "hockey", "NHL", aliases=("Hurricanes", "Canes", "Carolina", "CAR"), external_ids=_ids(("nhl:team", "CAR"))),
    IdentityEntity("nba.team.tor", "team", "Toronto Raptors", "basketball", "NBA", aliases=("Raptors", "Toronto", "TOR"), external_ids=_ids(("nba:team", "TOR"))),
    IdentityEntity("mlb.team.tor", "team", "Toronto Blue Jays", "baseball", "MLB", aliases=("Blue Jays", "Jays", "Toronto", "TOR"), external_ids=_ids(("mlb:team", "TOR"))),
    IdentityEntity("nfl.team.buf", "team", "Buffalo Bills", "football", "NFL", aliases=("Bills", "Buffalo", "BUF"), external_ids=_ids(("nfl:team", "BUF"))),
    IdentityEntity("uefa.team.sample_fc", "team", "Sample FC", "soccer", "UEFA", aliases=("Sample Football Club", "Sample"), external_ids=_ids(("uefa:club", "sample_fc", 0.9))),
    IdentityEntity("nhl.player.auston_matthews", "player", "Auston Matthews", "hockey", "NHL", team_id="nhl.team.tor", position="C", aliases=("Matthews", "Austin Matthews", "Auston Mathews", "Auston Mathtwes"), external_ids=_ids(("nhl:player", "auston_matthews")), metadata={"nationality": "United States"}),
    IdentityEntity("nhl.player.connor_mcdavid", "player", "Connor McDavid", "hockey", "NHL", team_id="nhl.team.edm", position="C", aliases=("McDavid", "McJesus"), external_ids=_ids(("nhl:player", "connor_mcdavid")), metadata={"nationality": "Canada"}),
    IdentityEntity("nhl.player.sebastian_aho_car", "player", "Sebastian Aho", "hockey", "NHL", team_id="nhl.team.car", position="C", aliases=("Finnish Sebastian Aho", "Sebastian Aho Carolina", "Aho Carolina"), external_ids=_ids(("nhl:player", "sebastian_aho_car")), metadata={"nationality": "Finland", "disambiguation_label": "Sebastian Aho — C — Carolina Hurricanes"}),
    IdentityEntity("nhl.player.sebastian_aho_swe", "player", "Sebastian Aho", "hockey", "NHL", team_id="", position="D", aliases=("Swedish Sebastian Aho", "Sebastian Aho Islanders", "Aho Sweden"), external_ids=_ids(("nhl:player", "sebastian_aho_swe")), metadata={"nationality": "Sweden", "disambiguation_label": "Sebastian Aho — D — Sweden / Islanders organization"}),
    IdentityEntity("nba.player.sample_guard", "player", "Sample Guard", "basketball", "NBA", team_id="nba.team.tor", position="G", aliases=("Example NBA Guard",), external_ids=_ids(("nba:player", "sample_guard", 0.8))),
    IdentityEntity("mlb.player.sample_pitcher", "player", "Sample Pitcher", "baseball", "MLB", team_id="mlb.team.tor", position="P", aliases=("Example MLB Pitcher",), external_ids=_ids(("mlb:player", "sample_pitcher", 0.8))),
)


class CrossSportIdentityRegistry:
    """Provider-neutral identity registry with sport-aware lookup indexes."""

    def __init__(self, entities: Sequence[IdentityEntity] | None = None) -> None:
        self.entities: tuple[IdentityEntity, ...] = tuple(entities or SEED_IDENTITY_ENTITIES)
        self._by_id: Dict[str, IdentityEntity] = {entity.entity_id: entity for entity in self.entities}
        self._by_name: Dict[str, list[IdentityEntity]] = {}
        self._by_external_id: Dict[str, IdentityEntity] = {}
        for entity in self.entities:
            for name in entity.normalized_names():
                self._by_name.setdefault(name, []).append(entity)
            for external in entity.external_ids:
                self._by_external_id[external.key()] = entity

    def all_entities(self) -> tuple[IdentityEntity, ...]:
        return self.entities

    def by_id(self, entity_id: str) -> IdentityEntity | None:
        return self._by_id.get(str(entity_id or ""))

    def by_external_id(self, namespace: str, value: str) -> IdentityEntity | None:
        key = f"{namespace.strip().lower()}:{value.strip().lower()}"
        return self._by_external_id.get(key)

    def search_name(self, query: str, sport: str = "", league: str = "", entity_type: str = "") -> tuple[IdentityEntity, ...]:
        key = " ".join(str(query or "").strip().lower().replace("-", " ").split())
        candidates = list(self._by_name.get(key, ()))
        if not candidates:
            # conservative substring fallback for typo-tolerant routing without taking
            # over the future Scout disambiguation layer.
            candidates = [entity for name, entities in self._by_name.items() if key and (key in name or name in key) for entity in entities]
        return tuple(_filter_entities(candidates, sport=sport, league=league, entity_type=entity_type))

    def stats(self) -> Dict[str, object]:
        by_type: Dict[str, int] = {}
        ambiguous: Dict[str, List[str]] = {}
        for entity in self.entities:
            by_type[entity.entity_type] = by_type.get(entity.entity_type, 0) + 1
        for name, entities in self._by_name.items():
            ids = sorted({entity.entity_id for entity in entities})
            if len(ids) > 1:
                ambiguous[name] = ids
        return {
            "entities": len(self.entities),
            "by_type": by_type,
            "sports": sorted({entity.sport for entity in self.entities}),
            "leagues": sorted({entity.league for entity in self.entities}),
            "ambiguous_names": ambiguous,
            "provider_neutral": all(entity.provider_neutral for entity in self.entities),
        }


def _filter_entities(items: Iterable[IdentityEntity], sport: str = "", league: str = "", entity_type: str = "") -> list[IdentityEntity]:
    sport_key = str(sport or "").strip().lower()
    league_key = str(league or "").strip().lower()
    type_key = str(entity_type or "").strip().lower()
    filtered: list[IdentityEntity] = []
    seen: set[str] = set()
    for entity in items:
        if entity.entity_id in seen:
            continue
        if sport_key and entity.sport.lower() != sport_key:
            continue
        if league_key and entity.league.lower() != league_key:
            continue
        if type_key and entity.entity_type.lower() != type_key:
            continue
        filtered.append(entity)
        seen.add(entity.entity_id)
    return filtered


def seed_identity_registry() -> CrossSportIdentityRegistry:
    return CrossSportIdentityRegistry()


def identity_key_for_provider(sport: str, league: str, entity_type: str, provider_key: str) -> str:
    """Create a stable provider-neutral lookup hint without persisting provider coupling."""
    return normalized_key(sport, league, entity_type, provider_key)
