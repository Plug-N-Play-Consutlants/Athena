"""Public entity registry for PIF-1 Build 002.

The registry is intentionally still seed-sized, but the structure now reflects
Athena's long-term public identity graph. Public-mode routing must resolve
entities here before it touches fantasy data or generic rulebook knowledge.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional


@dataclass(frozen=True)
class PublicEntity:
    entity_id: str
    entity_type: str
    canonical_name: str
    sport: str = "hockey"
    league: str = "NHL"
    team: str = ""
    position: str = ""
    nationality: str = ""
    birth_date: str = ""
    draft: str = ""
    status: str = "active"
    summary: str = ""
    aliases: List[str] = field(default_factory=list)
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "canonical_name": self.canonical_name,
            "sport": self.sport,
            "league": self.league,
            "team": self.team,
            "position": self.position,
            "nationality": self.nationality,
            "birth_date": self.birth_date,
            "draft": self.draft,
            "status": self.status,
            "summary": self.summary,
            "aliases": list(self.aliases),
            "metadata": dict(self.metadata),
        }


SEED_ENTITIES: List[PublicEntity] = [
    PublicEntity(
        entity_id="nhl.player.auston_matthews",
        entity_type="player",
        canonical_name="Auston Matthews",
        team="TOR",
        position="C",
        nationality="United States",
        birth_date="1997-09-17",
        draft="2016 NHL Draft, 1st overall, Toronto Maple Leafs",
        summary="Toronto Maple Leafs captain and elite goal-scoring center.",
        aliases=["matthews", "austin matthews", "auston mathews", "austom matthews", "mathtwes", "auston mathtwes"],
        metadata={"identity_tags": ["franchise superstar", "goal scorer", "captain"], "public_priority": 100},
    ),
    PublicEntity(
        "nhl.player.connor_mcdavid", "player", "Connor McDavid", team="EDM", position="C", nationality="Canada",
        birth_date="1997-01-13", draft="2015 NHL Draft, 1st overall, Edmonton Oilers",
        summary="Edmonton Oilers captain and generational play-driving center.",
        aliases=["mcdavid", "connor macdavid", "macdavid", "mcjesus"],
        metadata={"identity_tags": ["generational", "playmaker", "captain"], "public_priority": 100},
    ),
    PublicEntity("nhl.player.leon_draisaitl", "player", "Leon Draisaitl", team="EDM", position="C", nationality="Germany", birth_date="1995-10-27", draft="2014 NHL Draft, 3rd overall, Edmonton Oilers", summary="Elite German center and high-end scorer/playmaker.", aliases=["draisaitl", "drai", "leon drai"]),
    PublicEntity("nhl.player.cale_makar", "player", "Cale Makar", team="COL", position="D", nationality="Canada", birth_date="1998-10-30", draft="2017 NHL Draft, 4th overall, Colorado Avalanche", summary="Elite puck-moving defenseman and franchise cornerstone.", aliases=["makar"]),
    PublicEntity("nhl.player.nathan_mackinnon", "player", "Nathan MacKinnon", team="COL", position="C", nationality="Canada", birth_date="1995-09-01", draft="2013 NHL Draft, 1st overall, Colorado Avalanche", summary="Explosive Colorado Avalanche center and elite offensive driver.", aliases=["mackinnon", "mckinnon", "nathan mckinnen", "nathan mckinnon", "mac"]),
    PublicEntity("nhl.player.sidney_crosby", "player", "Sidney Crosby", team="PIT", position="C", nationality="Canada", birth_date="1987-08-07", draft="2005 NHL Draft, 1st overall, Pittsburgh Penguins", summary="Pittsburgh Penguins captain and era-defining two-way superstar.", aliases=["crosby", "sid", "sid the kid", "sydney crosby"]),
    PublicEntity("nhl.player.alex_ovechkin", "player", "Alex Ovechkin", team="WSH", position="LW", nationality="Russia", birth_date="1985-09-17", draft="2004 NHL Draft, 1st overall, Washington Capitals", summary="Washington Capitals captain and historic goal scorer.", aliases=["ovechkin", "ovi", "alexander ovechkin", "ove"]),
    PublicEntity("nhl.player.mitch_marner", "player", "Mitch Marner", team="TOR", position="RW", nationality="Canada", birth_date="1997-05-05", draft="2015 NHL Draft, 4th overall, Toronto Maple Leafs", summary="Creative Toronto winger known for playmaking and two-way usage.", aliases=["marner", "mitchell marner"]),
    PublicEntity("nhl.player.connor_bedard", "player", "Connor Bedard", team="CHI", position="C", nationality="Canada", birth_date="2005-07-17", draft="2023 NHL Draft, 1st overall, Chicago Blackhawks", summary="Chicago Blackhawks young franchise forward and elite shooting prospect turned NHL star.", aliases=["bedard"]),
    PublicEntity("nhl.player.macklin_celebrini", "player", "Macklin Celebrini", team="SJS", position="C", nationality="Canada", birth_date="2006-06-13", draft="2024 NHL Draft, 1st overall, San Jose Sharks", summary="San Jose Sharks top pick and foundational young center.", aliases=["celebrini", "macklin"]),
    PublicEntity("nhl.player.sebastian_aho_car", "player", "Sebastian Aho", team="CAR", position="C", nationality="Finland", birth_date="1997-07-26", draft="2015 NHL Draft, 35th overall, Carolina Hurricanes", aliases=["sebastian aho", "finnish sebastian aho", "sebastian aho carolina", "sebastian aho hurricanes", "aho carolina"], summary="Finnish Carolina Hurricanes center and top-line playmaker.", metadata={"disambiguation_label": "Sebastian Aho — C — Carolina Hurricanes — Finland"}),
    PublicEntity("nhl.player.sebastian_aho_swe", "player", "Sebastian Aho", team="NYI/AHL", position="D", nationality="Sweden", birth_date="1996-02-17", draft="2017 NHL Draft, 139th overall, New York Islanders", aliases=["sebastian aho", "swedish sebastian aho", "sebastian aho islanders", "sebastian aho penguins", "aho islanders", "aho sweden"], summary="Swedish puck-moving defenseman associated with the Islanders organization and Wilkes-Barre/Scranton Penguins.", metadata={"disambiguation_label": "Sebastian Aho — D — Sweden / Islanders organization"}),
    PublicEntity("nhl.team.toronto_maple_leafs", "team", "Toronto Maple Leafs", team="TOR", aliases=["toronto", "leafs", "maple leafs", "tor", "the leafs"], summary="Original Six NHL team based in Toronto."),
    PublicEntity("nhl.team.edmonton_oilers", "team", "Edmonton Oilers", team="EDM", aliases=["edmonton", "oilers", "edm"], summary="NHL team based in Edmonton."),
    PublicEntity("nhl.team.carolina_hurricanes", "team", "Carolina Hurricanes", team="CAR", aliases=["carolina", "hurricanes", "canes", "car"], summary="NHL team based in Raleigh, North Carolina."),
    PublicEntity("nhl.team.colorado_avalanche", "team", "Colorado Avalanche", team="COL", aliases=["colorado", "avalanche", "avs", "col"], summary="NHL team based in Denver."),
    PublicEntity("nhl.team.florida_panthers", "team", "Florida Panthers", team="FLA", aliases=["florida", "panthers", "fla", "florida panthers"], summary="NHL team based in Sunrise, Florida."),
    PublicEntity("nhl.team.dallas_stars", "team", "Dallas Stars", team="DAL", aliases=["dallas", "stars", "dallas stars", "dal"], summary="NHL team based in Dallas."),
    PublicEntity("nhl.team.chicago_blackhawks", "team", "Chicago Blackhawks", team="CHI", aliases=["chicago", "blackhawks", "hawks", "chi"], summary="Original Six NHL team based in Chicago."),
    PublicEntity("nhl.team.san_jose_sharks", "team", "San Jose Sharks", team="SJS", aliases=["san jose", "sharks", "sjs"], summary="NHL team based in San Jose."),
]


def all_entities() -> List[PublicEntity]:
    return list(SEED_ENTITIES)


def entities_by_type(entity_type: str) -> List[PublicEntity]:
    wanted = (entity_type or "").strip().lower()
    return [entity for entity in SEED_ENTITIES if entity.entity_type == wanted]


def find_by_id(entity_id: str) -> Optional[PublicEntity]:
    for entity in SEED_ENTITIES:
        if entity.entity_id == entity_id:
            return entity
    return None


def searchable_names(entity: PublicEntity) -> Iterable[str]:
    yield entity.canonical_name
    for alias in entity.aliases:
        yield alias


def registry_stats() -> Dict[str, object]:
    by_type: Dict[str, int] = {}
    aliases = 0
    ambiguous_names: Dict[str, int] = {}
    for entity in SEED_ENTITIES:
        by_type[entity.entity_type] = by_type.get(entity.entity_type, 0) + 1
        aliases += len(entity.aliases)
        key = entity.canonical_name.lower()
        ambiguous_names[key] = ambiguous_names.get(key, 0) + 1
    return {
        "entities": len(SEED_ENTITIES),
        "by_type": by_type,
        "aliases": aliases,
        "ambiguous_names": {name: count for name, count in ambiguous_names.items() if count > 1},
    }
