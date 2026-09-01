"""Intent-aware investigation strategy selection.

A strategy determines how deeply Athena should investigate and what capability
classes should be requested. It does not generate conclusions or render prose.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Iterable, Tuple

INVESTIGATION_STRATEGY_VERSION = "0.6.4.1.0"

@dataclass(frozen=True)
class InvestigationStrategy:
    strategy_id: str
    depth: str
    requested_capabilities: Tuple[str, ...]
    composition_profile: str
    maintain_working_state: bool
    discovery_mode: str
    preserve_rich_output: bool = False
    description: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["version"] = INVESTIGATION_STRATEGY_VERSION
        return data

CORE_STRATEGIES: Tuple[InvestigationStrategy, ...] = (
    InvestigationStrategy("brief_update", "concise", ("event_context",), "brief_update", False, "available", False, "Scores, standings, simple status and direct factual updates."),
    InvestigationStrategy("news_update", "concise", ("event_context", "timeline_context", "confidence"), "news_update", False, "available", False, "Current-event briefing with deeper discovery available on demand."),
    InvestigationStrategy("entity_profile", "rich", ("player_profile", "team_profile", "assessment", "historical_context", "confidence", "evidence_panel"), "entity_profile", True, "guided", True, "Rich player/team understanding; preserve dossier-style depth."),
    InvestigationStrategy("comparison", "rich", ("comparative_reasoning", "assessment", "historical_context", "confidence", "comparison_experience", "evidence_panel"), "comparison_experience", True, "guided", True, "Evidence-led comparison with explicit framework and tradeoffs."),
    InvestigationStrategy("deep_analysis", "deep", ("assessment", "organizational_context", "competitive_window", "historical_context", "confidence", "evidence_panel"), "investigation_experience", True, "active", True, "Multi-variable organizational or explanatory investigation."),
    InvestigationStrategy("advisory", "rich", ("assessment", "solution_comparison", "confidence", "evidence_panel"), "advisory_experience", True, "guided", True, "Decision support that preserves user judgment."),
    InvestigationStrategy("balanced", "standard", ("assessment", "confidence"), "standard_response", False, "available", False, "Fallback strategy for intents without a specialized experience."),
)

# Intent families remain declarative so new intents can be inserted without changing Scout rendering.
INTENT_STRATEGY_MAP: Dict[str, str] = {
    "score_update": "brief_update", "standings_update": "brief_update", "schedule_update": "brief_update",
    "live_event_intelligence": "news_update", "news_update": "news_update", "recent_events": "news_update",
    "public_player_profile": "entity_profile", "public_team_profile": "entity_profile", "public_entity_profile": "entity_profile",
    "public_player_comparison": "comparison", "public_team_comparison": "comparison",
    "public_team_window_analysis": "deep_analysis", "public_team_projection": "deep_analysis",
    "public_player_explainability": "deep_analysis", "public_organization_impact": "deep_analysis", "public_analytical_route": "deep_analysis",
    "fantasy_roster_diagnostic": "deep_analysis", "fantasy_trade_directions": "advisory", "fantasy_draft_strategy": "advisory",
    "fantasy_rebuild_detection": "deep_analysis", "fantasy_contract_rule": "advisory",
    "public_entity_disambiguation": "brief_update", "scout_runtime_diagnostics": "brief_update",
}

class InvestigationStrategyRegistry:
    def __init__(self, strategies: Iterable[InvestigationStrategy] | None = None) -> None:
        self._strategies = tuple(strategies or CORE_STRATEGIES)
        self._by_id = {item.strategy_id: item for item in self._strategies}

    def get(self, strategy_id: str) -> InvestigationStrategy:
        return self._by_id.get(str(strategy_id or "").strip().lower(), self._by_id["balanced"])

    def for_intent(self, intent: str) -> InvestigationStrategy:
        return self.get(INTENT_STRATEGY_MAP.get(str(intent or "").strip().lower(), "balanced"))

    def diagnostics(self) -> dict:
        return {"version": INVESTIGATION_STRATEGY_VERSION, "status": "pass", "strategies": [s.strategy_id for s in self._strategies], "intent_mappings": len(INTENT_STRATEGY_MAP)}

def select_investigation_strategy(intent: str, *, registry: InvestigationStrategyRegistry | None = None) -> InvestigationStrategy:
    return (registry or InvestigationStrategyRegistry()).for_intent(intent)

def strategy_diagnostics() -> dict:
    registry = InvestigationStrategyRegistry()
    samples = {intent: registry.for_intent(intent).strategy_id for intent in (
        "score_update", "live_event_intelligence", "public_player_profile", "public_player_comparison", "public_team_window_analysis", "fantasy_trade_directions"
    )}
    return {**registry.diagnostics(), "samples": samples}
