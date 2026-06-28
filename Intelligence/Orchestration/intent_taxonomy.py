"""Canonical intent taxonomy for Athena Intelligence Orchestration.

v0.5.6.0.0 introduces an intent-first layer above entity routing.  The
purpose of this module is not to answer questions; it defines stable analytical
intent labels that the Executive Planner and Scout acceptance harness can share.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


INTENT_FOUNDATION_VERSION = "0.5.6.0.0"


class IntentFamily(str, Enum):
    PROFILE = "profile"
    COMPARISON = "comparison"
    IMPACT = "impact"
    PROJECTION = "projection"
    HISTORICAL = "historical"
    FANTASY = "fantasy"
    RULES = "rules"
    EXPLANATION = "explanation"
    DISCOVERY = "discovery"
    UNKNOWN = "unknown"


class IntentType(str, Enum):
    PLAYER_PROFILE = "player_profile"
    TEAM_PROFILE = "team_profile"
    LEAGUE_PROFILE = "league_profile"
    PLAYER_COMPARISON = "player_comparison"
    TEAM_COMPARISON = "team_comparison"
    ORGANIZATIONAL_IMPACT = "organizational_impact"
    TRADE_IMPACT = "trade_impact"
    LINEUP_IMPACT = "lineup_impact"
    SALARY_CAP_IMPACT = "salary_cap_impact"
    PLAYER_PROJECTION = "player_projection"
    TEAM_PROJECTION = "team_projection"
    HISTORICAL_ANALYSIS = "historical_analysis"
    FANTASY_TRADE_ANALYSIS = "fantasy_trade_analysis"
    FANTASY_KEEPER_ANALYSIS = "fantasy_keeper_analysis"
    FANTASY_DRAFT_ANALYSIS = "fantasy_draft_analysis"
    LEAGUE_RULES = "league_rules"
    ROSTER_CONSTRUCTION = "roster_construction"
    CAUSAL_EXPLANATION = "causal_explanation"
    ENTITY_DISCOVERY = "entity_discovery"
    GENERAL_HELP = "general_help"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class IntentDefinition:
    intent: IntentType
    family: IntentFamily
    description: str
    required_capability_domains: List[str] = field(default_factory=list)
    optional_capability_domains: List[str] = field(default_factory=list)
    response_goal: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "intent": self.intent.value,
            "family": self.family.value,
            "description": self.description,
            "required_capability_domains": list(self.required_capability_domains),
            "optional_capability_domains": list(self.optional_capability_domains),
            "response_goal": self.response_goal,
        }


TAXONOMY: Dict[IntentType, IntentDefinition] = {
    IntentType.PLAYER_PROFILE: IntentDefinition(
        IntentType.PLAYER_PROFILE,
        IntentFamily.PROFILE,
        "Describe a player using public or league-specific player intelligence.",
        ["identity", "player_intelligence"],
        ["historical_intelligence", "trend_intelligence"],
        "Help the user understand who the player is and what matters analytically.",
    ),
    IntentType.TEAM_PROFILE: IntentDefinition(
        IntentType.TEAM_PROFILE,
        IntentFamily.PROFILE,
        "Describe a team using team identity and team intelligence.",
        ["identity", "team_intelligence"],
        ["reasoning", "historical_intelligence"],
        "Help the user understand the team's identity, strengths, weaknesses, and context.",
    ),
    IntentType.PLAYER_COMPARISON: IntentDefinition(
        IntentType.PLAYER_COMPARISON,
        IntentFamily.COMPARISON,
        "Compare two or more players around value, skill, projection, or fit.",
        ["identity", "player_intelligence", "comparison_reasoning"],
        ["historical_intelligence", "confidence"],
        "Give the user a decision-oriented comparison rather than parallel biographies.",
    ),
    IntentType.TEAM_COMPARISON: IntentDefinition(
        IntentType.TEAM_COMPARISON,
        IntentFamily.COMPARISON,
        "Compare two or more teams around quality, structure, or outlook.",
        ["identity", "team_intelligence", "comparison_reasoning"],
        ["historical_intelligence", "confidence"],
        "Explain relative team position and the causal drivers behind the comparison.",
    ),
    IntentType.ORGANIZATIONAL_IMPACT: IntentDefinition(
        IntentType.ORGANIZATIONAL_IMPACT,
        IntentFamily.IMPACT,
        "Explain how a player, event, or asset changes a team's structure or trajectory.",
        ["identity", "player_intelligence", "team_intelligence", "reasoning"],
        ["lineup_intelligence", "special_teams", "salary_cap", "projection_intelligence"],
        "Answer the user's underlying impact question across player, roster, cap, and window dimensions.",
    ),
    IntentType.ROSTER_CONSTRUCTION: IntentDefinition(
        IntentType.ROSTER_CONSTRUCTION,
        IntentFamily.IMPACT,
        "Evaluate how roster pieces fit together and where the structure is strong or weak.",
        ["team_intelligence", "reasoning"],
        ["player_intelligence", "salary_cap", "projection_intelligence"],
        "Translate talent into roster construction implications.",
    ),
    IntentType.PLAYER_PROJECTION: IntentDefinition(
        IntentType.PLAYER_PROJECTION,
        IntentFamily.PROJECTION,
        "Project a player's future trajectory or development path.",
        ["identity", "player_intelligence", "projection_intelligence"],
        ["historical_intelligence", "trend_intelligence"],
        "Explain future outlook with uncertainty and evidence boundaries.",
    ),
    IntentType.FANTASY_TRADE_ANALYSIS: IntentDefinition(
        IntentType.FANTASY_TRADE_ANALYSIS,
        IntentFamily.FANTASY,
        "Analyze fantasy trade value, incentives, and roster consequences.",
        ["league_context", "asset_valuation", "team_intelligence", "reasoning"],
        ["contracts", "draft_picks", "manager_behavior"],
        "Advise without commanding; surface incentives, alternatives, and risk.",
    ),
    IntentType.FANTASY_DRAFT_ANALYSIS: IntentDefinition(
        IntentType.FANTASY_DRAFT_ANALYSIS,
        IntentFamily.FANTASY,
        "Support fantasy draft preparation or draft-pick decision-making.",
        ["league_context", "draft_context", "player_intelligence"],
        ["contracts", "team_needs", "market"],
        "Turn league context into draft-prep priorities.",
    ),
    IntentType.LEAGUE_RULES: IntentDefinition(
        IntentType.LEAGUE_RULES,
        IntentFamily.RULES,
        "Explain rules, scoring, contracts, eligibility, or league settings.",
        ["rule_knowledge"],
        ["league_context", "citation_cards"],
        "Answer rule questions with explicit rule grounding.",
    ),
    IntentType.CAUSAL_EXPLANATION: IntentDefinition(
        IntentType.CAUSAL_EXPLANATION,
        IntentFamily.EXPLANATION,
        "Explain why a team, player, or event behaves a certain way.",
        ["identity", "reasoning"],
        ["player_intelligence", "team_intelligence", "historical_intelligence"],
        "Prioritize causal explanation over description.",
    ),
    IntentType.ENTITY_DISCOVERY: IntentDefinition(
        IntentType.ENTITY_DISCOVERY,
        IntentFamily.DISCOVERY,
        "Find, list, or disambiguate entities before analysis.",
        ["identity"],
        ["clarification"],
        "Resolve what the user means before deeper analysis.",
    ),
    IntentType.UNKNOWN: IntentDefinition(
        IntentType.UNKNOWN,
        IntentFamily.UNKNOWN,
        "No confident analytical intent was detected.",
        ["clarification"],
        [],
        "Ask for the smallest useful clarification or show supported examples.",
    ),
}


def definition_for(intent: IntentType) -> IntentDefinition:
    return TAXONOMY.get(intent, TAXONOMY[IntentType.UNKNOWN])


def taxonomy_diagnostics() -> Dict[str, object]:
    families: Dict[str, int] = {}
    for definition in TAXONOMY.values():
        families[definition.family.value] = families.get(definition.family.value, 0) + 1
    return {
        "version": INTENT_FOUNDATION_VERSION,
        "intent_count": len(TAXONOMY),
        "families": families,
        "intents": [definition.to_dict() for definition in TAXONOMY.values()],
    }
