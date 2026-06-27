"""Public team profile seed pack for PIF-1 Build 004.

The team pack gives public mode a real-world organization route so prompts like
"Tell me about the Leafs" do not fall through to player/fantasy/rulebook logic.
It is deliberately seed-sized; live standings, injuries, cap and transaction
feeds will enrich these profiles in later Event Intelligence builds.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from Knowledge.Intelligence.Entities.entity_registry import PublicEntity


@dataclass(frozen=True)
class PublicTeamProfile:
    entity_id: str
    display_name: str
    abbreviation: str
    league: str = "NHL"
    division: str = ""
    conference: str = ""
    identity: str = ""
    history: str = ""
    organizational_context: str = ""
    roster_context: str = ""
    competitive_identity: str = ""
    core_players: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    analytical_read: str = ""
    public_questions: List[str] = field(default_factory=list)
    known_limitations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "entity_id": self.entity_id,
            "display_name": self.display_name,
            "abbreviation": self.abbreviation,
            "league": self.league,
            "division": self.division,
            "conference": self.conference,
            "identity": self.identity,
            "history": self.history,
            "organizational_context": self.organizational_context,
            "roster_context": self.roster_context,
            "competitive_identity": self.competitive_identity,
            "core_players": list(self.core_players),
            "strengths": list(self.strengths),
            "risks": list(self.risks),
            "analytical_read": self.analytical_read,
            "public_questions": list(self.public_questions),
            "known_limitations": list(self.known_limitations),
        }


TEAMS: Dict[str, PublicTeamProfile] = {
    "nhl.team.toronto_maple_leafs": PublicTeamProfile(
        entity_id="nhl.team.toronto_maple_leafs",
        display_name="Toronto Maple Leafs",
        abbreviation="TOR",
        division="Atlantic",
        conference="Eastern",
        identity="Original Six NHL franchise based in Toronto, Ontario, with one of hockey's largest fan bases and one of the league's most scrutinized brands.",
        history="Founded in 1917, the franchise became the Toronto Maple Leafs in 1927. The club is part of the NHL's Original Six and has won 13 Stanley Cups, with its most recent championship in 1967.",
        organizational_context="Toronto's public evaluation usually centers on whether elite regular-season talent can translate into deeper playoff results.",
        roster_context="Seed context recognizes Matthews/Marner-style star-forward questions, but live roster, cap and transaction feeds are future inputs.",
        competitive_identity="High-skill regular-season contender under constant playoff scrutiny.",
        core_players=["Auston Matthews", "William Nylander", "Morgan Rielly"],
        strengths=["elite top-end scoring", "star center identity", "major-market resources"],
        risks=["playoff translation", "roster balance", "defensive depth", "cap pressure"],
        analytical_read="Toronto is best evaluated as a high-ceiling team whose public question is not talent, but whether structure, health, depth and postseason execution support the star core.",
        public_questions=["playoff ceiling", "star core", "market pressure", "roster balance"],
        known_limitations=["No live cap, injury, lineup, or current-season roster feed is attached to this seed profile yet."],
    ),
    "nhl.team.edmonton_oilers": PublicTeamProfile(
        entity_id="nhl.team.edmonton_oilers",
        display_name="Edmonton Oilers",
        abbreviation="EDM",
        division="Pacific",
        conference="Western",
        identity="NHL franchise based in Edmonton, Alberta, historically defined by elite center talent and high-end offensive creation.",
        history="The Oilers joined the NHL from the WHA in 1979 and became a dynasty in the 1980s, winning five Stanley Cups between 1984 and 1990.",
        organizational_context="Edmonton public analysis often focuses on maximizing McDavid/Draisaitl championship windows and supporting roster balance.",
        roster_context="Seed context recognizes elite offensive center questions; live goalie, defense, cap and depth evidence arrive later.",
        competitive_identity="Offense-first contender built around generational center talent.",
        core_players=["Connor McDavid", "Leon Draisaitl", "Evan Bouchard"],
        strengths=["elite offensive drivers", "power-play threat", "championship-window urgency"],
        risks=["defensive-zone structure", "goaltending volatility", "blue-line depth", "supporting cast balance"],
        analytical_read="Edmonton can be both dangerous and vulnerable: elite forwards can tilt games, but championship reliability depends on the support layer behind them.",
        public_questions=["championship window", "center depth", "defense", "goaltending"],
        known_limitations=["No live roster or playoff series feed is attached to this seed profile yet."],
    ),
    "nhl.team.carolina_hurricanes": PublicTeamProfile(
        entity_id="nhl.team.carolina_hurricanes",
        display_name="Carolina Hurricanes",
        abbreviation="CAR",
        division="Metropolitan",
        conference="Eastern",
        identity="NHL franchise based in Raleigh, North Carolina, known in the modern era for structure, possession play, and sustained contention.",
        history="The franchise began as the New England/Hartford Whalers before relocating to North Carolina in 1997. Carolina won the Stanley Cup in 2006.",
        organizational_context="Carolina questions commonly involve system strength, playoff finishing, center depth and whether scoring converts under pressure.",
        roster_context="Seed context connects Sebastian Aho to Carolina's top-line center identity; live deployment and transaction data are future inputs.",
        competitive_identity="System-driven contender built around pressure, possession and defensive structure.",
        core_players=["Sebastian Aho", "Andrei Svechnikov", "Jaccob Slavin"],
        strengths=["five-man structure", "forecheck pressure", "shot suppression", "organizational consistency"],
        risks=["finishing under playoff pressure", "top-end scoring conversion", "health"],
        analytical_read="Carolina is usually less about one superstar carrying the profile and more about whether its structured dominance converts into enough finishing in high-leverage games.",
        public_questions=["system strength", "playoff scoring", "center depth", "team structure"],
        known_limitations=["No live line-combination or injury feed is attached to this seed profile yet."],
    ),
    "nhl.team.colorado_avalanche": PublicTeamProfile(
        entity_id="nhl.team.colorado_avalanche",
        display_name="Colorado Avalanche",
        abbreviation="COL",
        division="Central",
        conference="Western",
        identity="NHL franchise based in Denver, Colorado, known for speed, skill, elite star power, and a proven championship peak.",
        history="The franchise began as the Quebec Nordiques, relocated to Colorado in 1995, and won Stanley Cups in 1996, 2001, and 2022.",
        organizational_context="Colorado analysis often starts with MacKinnon/Makar as franchise-level drivers and then evaluates depth, health and cap flexibility.",
        roster_context="Seed context recognizes top-end star power; live health/depth evidence is required for current evaluation.",
        competitive_identity="Speed-and-skill contender with championship proof at peak health.",
        core_players=["Nathan MacKinnon", "Cale Makar", "Mikko Rantanen"],
        strengths=["elite pace", "transition offense", "franchise defenseman", "championship ceiling"],
        risks=["health", "depth erosion", "cap-driven roster churn"],
        analytical_read="Colorado's ceiling remains tied to MacKinnon/Makar dominance, but the practical team grade depends on whether the middle of the roster is strong enough around them.",
        public_questions=["star core", "health", "defense", "championship window"],
        known_limitations=["No live injury, roster or cap feed is attached to this seed profile yet."],
    ),
    "nhl.team.florida_panthers": PublicTeamProfile(
        entity_id="nhl.team.florida_panthers",
        display_name="Florida Panthers",
        abbreviation="FLA",
        division="Atlantic",
        conference="Eastern",
        identity="NHL franchise based in Sunrise, Florida, known in the modern era for aggressive forechecking, depth, physicality, and championship-level team structure.",
        history="The Panthers entered the NHL in 1993, reached the Stanley Cup Final in 1996, and became a modern contender built around pressure, depth, and playoff-tested structure.",
        organizational_context="Florida analysis usually centers on whether its heavy, connected five-man style can keep suppressing opponents while supporting elite forwards and a deep blue line.",
        roster_context="Seed context recognizes Barkov/Tkachuk-style two-way identity, team depth, forecheck pressure, and playoff resilience; live roster, injury and cap evidence are future inputs.",
        competitive_identity="Heavy, connected, playoff-built contender with elite two-way structure.",
        core_players=["Aleksander Barkov", "Matthew Tkachuk", "Sergei Bobrovsky"],
        strengths=["forecheck pressure", "two-way center play", "depth", "playoff edge", "defensive buy-in"],
        risks=["health", "discipline", "cap retention", "mileage from long playoff runs"],
        analytical_read="Florida grades well because the identity is coherent: physical pressure, defensive support, top-end forwards, and depth all point in the same competitive direction.",
        public_questions=["championship identity", "forecheck", "two-way center", "depth", "playoff structure"],
        known_limitations=["No live roster, injury, cap, or current-season performance feed is attached to this seed profile yet."],
    ),
    "nhl.team.dallas_stars": PublicTeamProfile(
        entity_id="nhl.team.dallas_stars",
        display_name="Dallas Stars",
        abbreviation="DAL",
        division="Central",
        conference="Western",
        identity="NHL franchise based in Dallas, Texas, known in the modern era for balanced roster construction, strong two-way forward play, and a deep competitive core.",
        history="The franchise began as the Minnesota North Stars before relocating to Dallas in 1993. Dallas won the Stanley Cup in 1999 and has remained a recurring Western Conference contender in the modern era.",
        organizational_context="Dallas analysis usually centers on roster balance: veteran scoring, a strong young core, blue-line leadership, and goaltending that can support deep playoff runs.",
        roster_context="Seed context recognizes the Stars as a deep contender profile; live roster, injury, standings and cap feeds are future inputs.",
        competitive_identity="Balanced contender with depth, two-way structure, and multiple age bands contributing at once.",
        core_players=["Jason Robertson", "Roope Hintz", "Miro Heiskanen", "Jake Oettinger", "Wyatt Johnston"],
        strengths=["forward depth", "two-way structure", "goaltending ceiling", "elite defense anchor", "young core support"],
        risks=["top-line health", "playoff finishing", "veteran aging curve", "special-teams volatility"],
        analytical_read="Dallas grades as a strong team because its case is not dependent on one superstar; the roster profile combines scoring depth, defensive mobility, goaltending, and young contributors. The key question is whether that balanced profile produces enough finishing against elite playoff opponents.",
        public_questions=["contender status", "roster depth", "playoff ceiling", "young core", "goaltending"],
        known_limitations=["No live roster, injury, cap, standings, or current-season performance feed is attached to this seed profile yet."],
    ),

}


def get_public_team_profile(entity_id: str) -> Optional[PublicTeamProfile]:
    return TEAMS.get(entity_id)


def profile_for_team_entity(entity: PublicEntity | None) -> Optional[PublicTeamProfile]:
    if entity is None:
        return None
    return get_public_team_profile(entity.entity_id)


def public_team_profiles() -> List[PublicTeamProfile]:
    return list(TEAMS.values())


def public_team_profile_stats() -> Dict[str, object]:
    return {
        "teams": len(TEAMS),
        "questions_seeded": sum(len(team.public_questions) for team in TEAMS.values()),
        "guardrails": [
            "Public team answers use team identity/context before fantasy league data.",
            "Seed team profiles are not a substitute for live roster, cap, injury, standings or transaction feeds.",
        ],
    }
