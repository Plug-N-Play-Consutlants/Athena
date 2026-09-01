"""Public player profile seed pack for PIF-1 Build 004.

This is a deliberately small, structured public-knowledge layer. Its purpose is
not to be a complete NHL database yet; it gives Athena a public-first identity
and comparison substrate so public Scout prompts do not fall back to fantasy
owner data or unrelated rulebook/MOU packs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from Knowledge.Intelligence.Entities.entity_registry import PublicEntity, find_by_id


@dataclass(frozen=True)
class PublicPlayerProfile:
    entity_id: str
    display_name: str
    position: str
    team: str
    nationality: str = ""
    draft: str = ""
    role: str = ""
    style: str = ""
    career_identity: str = ""
    career_notes: List[str] = field(default_factory=list)
    awards: List[str] = field(default_factory=list)
    public_value: str = ""
    physical_profile: str = ""
    current_context: str = ""
    international_context: str = ""
    analytical_notes: List[str] = field(default_factory=list)
    fantasy_context: str = ""
    known_limitations: List[str] = field(default_factory=list)
    comparison_tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "entity_id": self.entity_id,
            "display_name": self.display_name,
            "position": self.position,
            "team": self.team,
            "nationality": self.nationality,
            "draft": self.draft,
            "role": self.role,
            "style": self.style,
            "career_identity": self.career_identity,
            "career_notes": list(self.career_notes),
            "awards": list(self.awards),
            "public_value": self.public_value,
            "physical_profile": self.physical_profile,
            "current_context": self.current_context,
            "international_context": self.international_context,
            "analytical_notes": list(self.analytical_notes),
            "fantasy_context": self.fantasy_context,
            "known_limitations": list(self.known_limitations),
            "comparison_tags": list(self.comparison_tags),
        }


PROFILES: Dict[str, PublicPlayerProfile] = {
    "nhl.player.auston_matthews": PublicPlayerProfile(
        entity_id="nhl.player.auston_matthews",
        display_name="Auston Matthews",
        position="C",
        team="TOR",
        nationality="United States",
        draft="2016 NHL Draft, 1st overall, Toronto Maple Leafs",
        role="franchise goal-scoring center and Toronto captain",
        style="elite shot generation, high-end finishing, heavy power-play impact, and improving two-way center usage",
        career_identity="Matthews is best understood as a modern franchise center whose defining public profile is elite goal scoring rather than simple point accumulation.",
        career_notes=[
            "First-overall draft pedigree gives him long-standing organizational-franchise context.",
            "His peak seasons establish him as one of the NHL's premier goal scorers of this era.",
            "Captaincy adds leadership and organizational-value context beyond box-score production.",
        ],
        awards=["Hart Trophy", "Ted Lindsay Award", "Calder Trophy", "Rocket Richard Trophy"],
        public_value="Franchise superstar / elite goal-scoring center",
        physical_profile="6 foot 3, 215-pound center with a deceptive release and rare inside-slot finishing skill.",
        current_context="Toronto captain since 2024; recent production should be read against injury, usage, coaching, and role context rather than treated as a clean talent decline.",
        international_context="United States national-team cornerstone. Seed profile tracks international context but does not assert medal results without verified event evidence.",
        analytical_notes=[
            "His value is driven by goal creation more than raw assist volume; a points-only view can understate how unusual his goal-scoring profile is.",
            "A recent drop from peak output is a trend signal, not a completed deterioration finding, until health, shooting volume, power-play deployment, and coaching usage are evaluated.",
            "The captaincy matters analytically because it changes the public/team role from elite scorer to franchise standard-bearer.",
        ],
        fantasy_context="In goals-plus-assists formats he remains a premium keeper asset, but short-term valuation should account for health, games played, and whether the format rewards goals separately.",
        known_limitations=["PIF Build 004 does not yet ingest live injuries, line deployment, or current-season official statistics automatically."],
        comparison_tags=["goal_scoring", "franchise_center", "power_play", "captain", "elite_finisher"],
    ),
    "nhl.player.connor_mcdavid": PublicPlayerProfile(
        entity_id="nhl.player.connor_mcdavid",
        display_name="Connor McDavid",
        position="C",
        team="EDM",
        nationality="Canada",
        draft="2015 NHL Draft, 1st overall, Edmonton Oilers",
        role="generational play-driving center and Edmonton captain",
        style="unmatched speed through the neutral zone, elite puck control, transition creation, and high-end playmaking",
        career_identity="McDavid is the NHL's defining offensive driver of his generation, with value rooted in pace, creation, and sustained scoring dominance.",
        career_notes=[
            "First-overall draft pedigree and captaincy anchor his public identity as a franchise centerpiece.",
            "His Art Ross/Hart-level résumé supports generational-offense classification.",
            "His impact is not limited to points; he changes defensive structures through speed and puck pressure.",
        ],
        awards=["Hart Trophy", "Art Ross Trophy", "Ted Lindsay Award", "Conn Smythe Trophy"],
        public_value="Generational franchise superstar / elite offensive driver",
        known_limitations=["PIF Build 004 does not yet ingest live injuries, teammate deployment, or current official game logs automatically."],
        comparison_tags=["playmaking", "transition", "speed", "franchise_center", "generational"],
    ),
    "nhl.player.leon_draisaitl": PublicPlayerProfile(
        entity_id="nhl.player.leon_draisaitl",
        display_name="Leon Draisaitl",
        position="C/LW",
        team="EDM",
        nationality="Germany",
        draft="2014 NHL Draft, 3rd overall, Edmonton Oilers",
        role="elite offensive forward and top-tier power-play finisher/playmaker",
        style="puck protection, half-wall power-play creation, finishing touch, and elite passing in tight spaces",
        career_identity="Draisaitl profiles as an elite offensive force whose public value sits between franchise centerpiece and championship-level offensive pillar.",
        career_notes=["Hart/Art Ross calibre peak supports elite-public-player classification.", "Can drive offense as either a center or wing depending on deployment."],
        awards=["Hart Trophy", "Art Ross Trophy", "Ted Lindsay Award"],
        public_value="Elite offensive superstar",
        known_limitations=["Role and deployment should be refreshed when live lineup data is added."],
        comparison_tags=["playmaking", "power_play", "finishing", "elite_offense"],
    ),
    "nhl.player.nathan_mackinnon": PublicPlayerProfile(
        entity_id="nhl.player.nathan_mackinnon",
        display_name="Nathan MacKinnon",
        position="C",
        team="COL",
        nationality="Canada",
        draft="2013 NHL Draft, 1st overall, Colorado Avalanche",
        role="franchise center and pace-driving offensive centerpiece",
        style="explosive skating, rush offense, shot volume, and high-tempo puck carrying",
        career_identity="MacKinnon is a franchise center whose best public comparisons emphasize pace, shot pressure, and playoff-tested offensive impact.",
        career_notes=["First-overall pick and Stanley Cup core piece.", "Peak seasons place him among the NHL's most dangerous offensive players."],
        awards=["Hart Trophy", "Calder Trophy", "Stanley Cup"],
        public_value="Franchise superstar / pace-driving center",
        known_limitations=["PIF Build 004 has no live injury or shift/deployment feed yet."],
        comparison_tags=["speed", "rush_offense", "shot_volume", "franchise_center"],
    ),
    "nhl.player.sidney_crosby": PublicPlayerProfile(
        entity_id="nhl.player.sidney_crosby",
        display_name="Sidney Crosby",
        position="C",
        team="PIT",
        nationality="Canada",
        draft="2005 NHL Draft, 1st overall, Pittsburgh Penguins",
        role="all-time franchise center and era-defining captain",
        style="complete center play, edge work, puck protection, faceoff/detail excellence, and elite hockey sense",
        career_identity="Crosby is an all-time great whose public profile combines production, championships, leadership, and complete-center impact.",
        career_notes=["Multiple Stanley Cups and major awards establish legacy value.", "Still useful as a benchmark for complete-center comparison questions."],
        awards=["Stanley Cup", "Hart Trophy", "Conn Smythe Trophy", "Art Ross Trophy"],
        public_value="All-time franchise cornerstone",
        known_limitations=["Current-year production and injury context require live feeds in a later build."],
        comparison_tags=["legacy", "complete_center", "championship", "leadership"],
    ),
    "nhl.player.alex_ovechkin": PublicPlayerProfile(
        entity_id="nhl.player.alex_ovechkin",
        display_name="Alex Ovechkin",
        position="LW",
        team="WSH",
        nationality="Russia",
        draft="2004 NHL Draft, 1st overall, Washington Capitals",
        role="all-time goal-scoring winger and franchise icon",
        style="one-timer threat, volume shooting, physical power winger profile, and historically rare finishing longevity",
        career_identity="Ovechkin is a historically significant goal scorer whose public questions should be framed around goal-scoring legacy, longevity, and era context.",
        career_notes=["Rocket Richard résumé and all-time goal chase define his public profile.", "Stanley Cup win adds legacy completeness beyond goal totals."],
        awards=["Stanley Cup", "Hart Trophy", "Rocket Richard Trophy", "Conn Smythe Trophy"],
        public_value="All-time goal-scoring icon",
        known_limitations=["PIF Build 004 does not yet run full era-adjusted goal models."],
        comparison_tags=["goal_scoring", "legacy", "shooting", "power_winger"],
    ),
    "nhl.player.cale_makar": PublicPlayerProfile(
        entity_id="nhl.player.cale_makar",
        display_name="Cale Makar",
        position="D",
        team="COL",
        nationality="Canada",
        draft="2017 NHL Draft, 4th overall, Colorado Avalanche",
        role="elite modern offensive defenseman and transition driver",
        style="edgework, puck transport, offensive-zone creation, power-play quarterbacking, and high-end defensive recovery speed",
        career_identity="Makar represents the modern elite defense archetype: a defenseman whose value comes from transition control as much as traditional defending.",
        career_notes=["Stanley Cup and major individual awards support franchise-defenseman classification.", "Useful benchmark for puck-moving defensemen."],
        awards=["Stanley Cup", "Norris Trophy", "Conn Smythe Trophy", "Calder Trophy"],
        public_value="Franchise defenseman / elite puck mover",
        known_limitations=["Full defensive impact metrics require future shot-quality and transition-data packs."],
        comparison_tags=["defense", "transition", "puck_moving", "power_play"],
    ),
    "nhl.player.connor_bedard": PublicPlayerProfile(
        entity_id="nhl.player.connor_bedard",
        display_name="Connor Bedard",
        position="C",
        team="CHI",
        nationality="Canada",
        draft="2023 NHL Draft, 1st overall, Chicago Blackhawks",
        role="young franchise forward and primary offensive building block",
        style="elite release, high-end puck skill, offensive imagination, and scoring creation from dangerous areas",
        career_identity="Bedard is Chicago's young franchise-forward bet: the upside case is driven by rare scoring tools and age-adjusted offensive translation.",
        career_notes=[
            "First-overall draft pedigree anchors his public projection profile.",
            "The elite outcome depends on skill translation plus roster support, not points alone.",
            "Useful as a canonical test for prospect-to-franchise-player reasoning.",
        ],
        awards=["Calder Trophy"],
        public_value="Young franchise cornerstone / elite-offense projection",
        physical_profile="Compact offensive center profile with rare shooting talent and high skill density.",
        current_context="Chicago's development environment, linemate quality, power-play structure, and roster insulation are central to his projection.",
        analytical_notes=[
            "High-end shooting and puck skill give him a credible elite-driver path.",
            "Development context and team support are major swing factors.",
            "Production should be interpreted through age, usage, and team environment.",
        ],
        known_limitations=["Full projection requires richer deployment, shot-quality, teammate, injury, and development-curve feeds."],
        comparison_tags=["projection", "shooting", "young_core", "franchise_forward", "development"],
    ),
    "nhl.player.sebastian_aho_car": PublicPlayerProfile(
        entity_id="nhl.player.sebastian_aho_car",
        display_name="Sebastian Aho",
        position="C",
        team="CAR",
        nationality="Finland",
        draft="2015 NHL Draft, 35th overall, Carolina Hurricanes",
        role="top-line Carolina center and high-end playmaker",
        style="smart two-way center play, pace, playmaking, finishing touch, and special-teams utility",
        career_identity="The Finnish Sebastian Aho is a Carolina franchise forward, not the Swedish defenseman with the same name.",
        career_notes=["Born July 26, 1997 in Rauma, Finland.", "Public ambiguity must distinguish him from the Swedish defenseman Sebastian Aho."],
        awards=[],
        public_value="Top-line NHL center / franchise forward",
        known_limitations=["Championship and current-team statements should be refreshed from live sources before public release."],
        comparison_tags=["center", "playmaking", "two_way", "carolina"],
    ),
    "nhl.player.sebastian_aho_swe": PublicPlayerProfile(
        entity_id="nhl.player.sebastian_aho_swe",
        display_name="Sebastian Aho",
        position="D",
        team="NYI/AHL",
        nationality="Sweden",
        draft="2017 NHL Draft, 139th overall, New York Islanders",
        role="puck-moving defenseman associated with the Islanders organization and Wilkes-Barre/Scranton Penguins",
        style="mobile puck-moving defense profile with depth/organizational usage",
        career_identity="The Swedish Sebastian Aho is a defenseman and must remain a separate entity from Carolina's Finnish center.",
        career_notes=["Born February 17, 1996 in Umeå, Sweden.", "The same-name overlap with Carolina's Sebastian Aho is a canonical ambiguity test for Athena."],
        awards=[],
        public_value="Depth/puck-moving defenseman",
        known_limitations=["Current organization/status should be refreshed from live provider data before public release."],
        comparison_tags=["defense", "puck_moving", "ambiguity_case"],
    ),
}


def get_public_player_profile(entity_id: str) -> Optional[PublicPlayerProfile]:
    return PROFILES.get(entity_id)


def public_player_profiles() -> List[PublicPlayerProfile]:
    return list(PROFILES.values())


def profile_for_entity(entity: PublicEntity | None) -> Optional[PublicPlayerProfile]:
    if entity is None:
        return None
    return get_public_player_profile(entity.entity_id)


def public_profile_stats() -> Dict[str, object]:
    awards = sum(len(profile.awards) for profile in PROFILES.values())
    tags = sorted({tag for profile in PROFILES.values() for tag in profile.comparison_tags})
    return {
        "profiles": len(PROFILES),
        "awards_seeded": awards,
        "comparison_tags": tags,
        "guardrails": [
            "Public player answers use public identity/profile data before fantasy outputs.",
            "Fantasy context is optional and must not dominate public comparison answers.",
            "Live official statistics and news feeds are future PIF/Event Intelligence inputs.",
            "PIF Build 004 adds seeded public team context and richer comparison sections before live data feeds.",
        ],
    }
