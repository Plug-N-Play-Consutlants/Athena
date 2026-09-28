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
    IdentityEntity("nhl.team.ana", "team", 'Anaheim Ducks', "hockey", "NHL", aliases=('Ducks', 'Anaheim', 'ANA',), external_ids=_ids(("nhl:team", "ANA"))),
    IdentityEntity("nhl.team.bos", "team", 'Boston Bruins', "hockey", "NHL", aliases=('Bruins', 'Boston', 'BOS',), external_ids=_ids(("nhl:team", "BOS"))),
    IdentityEntity("nhl.team.buf", "team", 'Buffalo Sabres', "hockey", "NHL", aliases=('Sabres', 'Buffalo', 'BUF',), external_ids=_ids(("nhl:team", "BUF"))),
    IdentityEntity("nhl.team.cgy", "team", 'Calgary Flames', "hockey", "NHL", aliases=('Flames', 'Calgary', 'CGY',), external_ids=_ids(("nhl:team", "CGY"))),
    IdentityEntity("nhl.team.car", "team", 'Carolina Hurricanes', "hockey", "NHL", aliases=('Hurricanes', 'Canes', 'Carolina', 'CAR',), external_ids=_ids(("nhl:team", "CAR"))),
    IdentityEntity("nhl.team.chi", "team", 'Chicago Blackhawks', "hockey", "NHL", aliases=('Blackhawks', 'Hawks', 'Chicago', 'CHI',), external_ids=_ids(("nhl:team", "CHI"))),
    IdentityEntity("nhl.team.col", "team", 'Colorado Avalanche', "hockey", "NHL", aliases=('Avalanche', 'Avs', 'Colorado', 'COL',), external_ids=_ids(("nhl:team", "COL"))),
    IdentityEntity("nhl.team.cbj", "team", 'Columbus Blue Jackets', "hockey", "NHL", aliases=('Blue Jackets', 'Columbus', 'CBJ',), external_ids=_ids(("nhl:team", "CBJ"))),
    IdentityEntity("nhl.team.dal", "team", 'Dallas Stars', "hockey", "NHL", aliases=('Stars', 'Dallas', 'DAL',), external_ids=_ids(("nhl:team", "DAL"))),
    IdentityEntity("nhl.team.det", "team", 'Detroit Red Wings', "hockey", "NHL", aliases=('Red Wings', 'Detroit', 'DET',), external_ids=_ids(("nhl:team", "DET"))),
    IdentityEntity("nhl.team.edm", "team", 'Edmonton Oilers', "hockey", "NHL", aliases=('Oilers', 'Edmonton', 'EDM',), external_ids=_ids(("nhl:team", "EDM"))),
    IdentityEntity("nhl.team.fla", "team", 'Florida Panthers', "hockey", "NHL", aliases=('Panthers', 'Florida', 'FLA',), external_ids=_ids(("nhl:team", "FLA"))),
    IdentityEntity("nhl.team.lak", "team", 'Los Angeles Kings', "hockey", "NHL", aliases=('LA Kings', 'Kings', 'Los Angeles', 'LAK',), external_ids=_ids(("nhl:team", "LAK"))),
    IdentityEntity("nhl.team.min", "team", 'Minnesota Wild', "hockey", "NHL", aliases=('Wild', 'Minnesota', 'MIN',), external_ids=_ids(("nhl:team", "MIN"))),
    IdentityEntity("nhl.team.mtl", "team", 'Montreal Canadiens', "hockey", "NHL", aliases=('Canadiens', 'Habs', 'Montreal', 'MTL',), external_ids=_ids(("nhl:team", "MTL"))),
    IdentityEntity("nhl.team.nsh", "team", 'Nashville Predators', "hockey", "NHL", aliases=('Predators', 'Preds', 'Nashville', 'NSH',), external_ids=_ids(("nhl:team", "NSH"))),
    IdentityEntity("nhl.team.njd", "team", 'New Jersey Devils', "hockey", "NHL", aliases=('Devils', 'New Jersey', 'NJD',), external_ids=_ids(("nhl:team", "NJD"))),
    IdentityEntity("nhl.team.nyi", "team", 'New York Islanders', "hockey", "NHL", aliases=('Islanders', 'NY Islanders', 'New York Islanders', 'NYI',), external_ids=_ids(("nhl:team", "NYI"))),
    IdentityEntity("nhl.team.nyr", "team", 'New York Rangers', "hockey", "NHL", aliases=('Rangers', 'NY Rangers', 'New York Rangers', 'NYR',), external_ids=_ids(("nhl:team", "NYR"))),
    IdentityEntity("nhl.team.ott", "team", 'Ottawa Senators', "hockey", "NHL", aliases=('Senators', 'Sens', 'Ottawa', 'OTT',), external_ids=_ids(("nhl:team", "OTT"))),
    IdentityEntity("nhl.team.phi", "team", 'Philadelphia Flyers', "hockey", "NHL", aliases=('Flyers', 'Philadelphia', 'PHI',), external_ids=_ids(("nhl:team", "PHI"))),
    IdentityEntity("nhl.team.pit", "team", 'Pittsburgh Penguins', "hockey", "NHL", aliases=('Penguins', 'Pens', 'Pittsburgh', 'PIT',), external_ids=_ids(("nhl:team", "PIT"))),
    IdentityEntity("nhl.team.sjs", "team", 'San Jose Sharks', "hockey", "NHL", aliases=('Sharks', 'San Jose', 'SJS',), external_ids=_ids(("nhl:team", "SJS"))),
    IdentityEntity("nhl.team.sea", "team", 'Seattle Kraken', "hockey", "NHL", aliases=('Kraken', 'Seattle', 'SEA',), external_ids=_ids(("nhl:team", "SEA"))),
    IdentityEntity("nhl.team.stl", "team", 'St. Louis Blues', "hockey", "NHL", aliases=('Blues', 'St Louis', 'St. Louis', 'STL',), external_ids=_ids(("nhl:team", "STL"))),
    IdentityEntity("nhl.team.tbl", "team", 'Tampa Bay Lightning', "hockey", "NHL", aliases=('Lightning', 'Tampa Bay', 'Tampa', 'TBL',), external_ids=_ids(("nhl:team", "TBL"))),
    IdentityEntity("nhl.team.tor", "team", 'Toronto Maple Leafs', "hockey", "NHL", aliases=('Leafs', 'Maple Leafs', 'Toronto', 'TOR',), external_ids=_ids(("nhl:team", "TOR"))),
    IdentityEntity("nhl.team.uta", "team", 'Utah Mammoth', "hockey", "NHL", aliases=('Mammoth', 'Utah', 'UTA',), external_ids=_ids(("nhl:team", "UTA"))),
    IdentityEntity("nhl.team.van", "team", 'Vancouver Canucks', "hockey", "NHL", aliases=('Canucks', 'Vancouver', 'VAN',), external_ids=_ids(("nhl:team", "VAN"))),
    IdentityEntity("nhl.team.vgk", "team", 'Vegas Golden Knights', "hockey", "NHL", aliases=('Golden Knights', 'Vegas', 'VGK',), external_ids=_ids(("nhl:team", "VGK"))),
    IdentityEntity("nhl.team.wsh", "team", 'Washington Capitals', "hockey", "NHL", aliases=('Capitals', 'Caps', 'Washington', 'WSH',), external_ids=_ids(("nhl:team", "WSH"))),
    IdentityEntity("nhl.team.wpg", "team", 'Winnipeg Jets', "hockey", "NHL", aliases=('Jets', 'Winnipeg', 'WPG',), external_ids=_ids(("nhl:team", "WPG"))),
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
