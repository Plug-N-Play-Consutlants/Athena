"""Registry-driven intelligence modules for Athena.

This is a foundation layer: it declares sport-aware module families, capability
metadata, and deterministic routing hints. Later sprints can attach deeper
reasoning implementations behind the same contract.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Iterable, Tuple

try:
    from Sports import seed_sport_registry
except Exception:  # pragma: no cover
    seed_sport_registry = None  # type: ignore

INTELLIGENCE_FOUNDATION_VERSION = "0.5.5.0.0"


@dataclass(frozen=True)
class IntelligenceModule:
    module_id: str
    family: str
    label: str
    description: str
    supported_sports: Tuple[str, ...]
    inputs: Tuple[str, ...]
    outputs: Tuple[str, ...]
    evidence_sources: Tuple[str, ...]
    status: str = "foundation"
    provider_neutral: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def supports(self, sport: str = "") -> bool:
        key = str(sport or "").strip().lower()
        return not key or "all" in self.supported_sports or key in self.supported_sports

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


CORE_MODULES: Tuple[IntelligenceModule, ...] = (
    IntelligenceModule("player_assessment", "assessment", "Player Assessment", "Evaluates player profile, role, production, context, and uncertainty.", ("all",), ("identity", "knowledge", "history", "events"), ("assessment", "confidence", "explanation"), ("identity_registry", "knowledge_graph", "historical_intelligence", "event_intelligence")),
    IntelligenceModule("team_assessment", "assessment", "Team Assessment", "Evaluates team profile, roster context, schedule, form, and event context.", ("all",), ("identity", "knowledge", "events"), ("assessment", "summary", "confidence"), ("identity_registry", "knowledge_graph", "event_intelligence")),
    IntelligenceModule("game_assessment", "assessment", "Game Assessment", "Frames game or matchup context with sport-aware terminology and evidence.", ("all",), ("schedule", "team", "events"), ("matchup_context", "scenario_notes"), ("event_intelligence", "schedule_context")),
    IntelligenceModule("season_assessment", "assessment", "Season Assessment", "Summarizes season-long context, trends, and standing implications.", ("all",), ("history", "schedule", "knowledge"), ("season_context", "trend_summary"), ("historical_intelligence", "knowledge_graph")),
    IntelligenceModule("schedule_assessment", "assessment", "Schedule Assessment", "Assesses schedule density, sequence, rest, travel, and upcoming event windows.", ("all",), ("schedule", "events"), ("schedule_context", "risk_flags"), ("event_intelligence", "provider_schedule")),
    IntelligenceModule("event_assessment", "assessment", "Event Assessment", "Normalizes events into impact, confidence, corroboration, and timeline context.", ("all",), ("events", "sources", "identity"), ("event_context", "impact", "confidence"), ("event_intelligence", "source_profiles", "identity_registry")),
    IntelligenceModule("historical_assessment", "assessment", "Historical Assessment", "Uses historical snapshots, comparisons, and trends as evidence.", ("all",), ("history", "identity"), ("trend_context", "comparables", "confidence"), ("historical_intelligence", "trend_engine")),
    IntelligenceModule("draft_assessment", "fantasy", "Draft Assessment", "Frames draft, keeper, and asset context without taking over manager decisions.", ("hockey", "football", "basketball", "baseball"), ("league_rules", "identity", "roster"), ("draft_context", "options", "uncertainty"), ("knowledge_graph", "league_rules", "identity_registry")),
    IntelligenceModule("trade_assessment", "fantasy", "Trade Assessment", "Evaluates trade context, surplus/deficit, term, assets, and uncertainty.", ("hockey", "football", "basketball", "baseball"), ("roster", "contracts", "identity", "history"), ("trade_context", "risk", "confidence"), ("knowledge_graph", "historical_intelligence", "league_rules")),
    IntelligenceModule("roster_assessment", "fantasy", "Roster Assessment", "Assesses roster shape, positional balance, depth, constraints, and scenario options.", ("hockey", "football", "basketball", "baseball"), ("roster", "identity", "league_rules"), ("roster_context", "needs", "options"), ("knowledge_graph", "identity_registry", "league_rules")),
)


class IntelligenceRegistry:
    def __init__(self, modules: Iterable[IntelligenceModule] | None = None) -> None:
        self._modules: Tuple[IntelligenceModule, ...] = tuple(modules or CORE_MODULES)
        self._by_id = {module.module_id: module for module in self._modules}

    def all_modules(self) -> Tuple[IntelligenceModule, ...]:
        return self._modules

    def get(self, module_id: str) -> IntelligenceModule | None:
        return self._by_id.get(str(module_id or "").strip().lower())

    def for_sport(self, sport: str) -> Tuple[IntelligenceModule, ...]:
        return tuple(module for module in self._modules if module.supports(sport))

    def stats(self) -> Dict[str, Any]:
        families: Dict[str, int] = {}
        for module in self._modules:
            families[module.family] = families.get(module.family, 0) + 1
        return {
            "version": INTELLIGENCE_FOUNDATION_VERSION,
            "modules": len(self._modules),
            "module_ids": sorted(module.module_id for module in self._modules),
            "families": families,
            "provider_neutral": all(module.provider_neutral for module in self._modules),
            "statuses": sorted({module.status for module in self._modules}),
        }


def seed_intelligence_registry() -> IntelligenceRegistry:
    return IntelligenceRegistry()


def select_intelligence_modules(intent: str = "general", sport: str = "", entity_type: str = "") -> Tuple[IntelligenceModule, ...]:
    registry = seed_intelligence_registry()
    intent_key = str(intent or "general").lower()
    type_key = str(entity_type or "").lower()
    preferred: Tuple[str, ...]
    if intent_key == "comparison":
        preferred = ("player_assessment", "team_assessment", "historical_assessment")
    elif intent_key == "event_context":
        preferred = ("event_assessment", "schedule_assessment")
    elif intent_key in {"profile", "summary"} and type_key == "team":
        preferred = ("team_assessment", "season_assessment", "event_assessment")
    elif intent_key in {"profile", "summary"}:
        preferred = ("player_assessment", "historical_assessment", "event_assessment")
    elif intent_key in {"draft", "trade", "roster"}:
        preferred = (f"{intent_key}_assessment", "player_assessment", "team_assessment")
    else:
        preferred = ("player_assessment", "team_assessment", "event_assessment")
    selected = []
    for module_id in preferred:
        module = registry.get(module_id)
        if module and module.supports(sport):
            selected.append(module)
    return tuple(selected)


def capability_matrix() -> Dict[str, Any]:
    registry = seed_intelligence_registry()
    sport_registry = seed_sport_registry() if seed_sport_registry else None
    sports = [sport.sport_id for sport in sport_registry.all_sports()] if sport_registry else ["hockey", "football", "baseball", "basketball", "soccer"]
    rows = []
    for sport in sports:
        modules = registry.for_sport(sport)
        rows.append({
            "sport": sport,
            "module_count": len(modules),
            "modules": [module.module_id for module in modules],
            "capabilities": sorted({source for module in modules for source in module.evidence_sources}),
        })
    return {
        "version": INTELLIGENCE_FOUNDATION_VERSION,
        "status": "pass" if rows and registry.stats()["modules"] >= 10 else "warn",
        "registry": registry.stats(),
        "sports": rows,
    }


def studio_intelligence_diagnostics() -> Dict[str, Any]:
    matrix = capability_matrix()
    return {
        "panel": "intelligence",
        "status": matrix["status"],
        "version": INTELLIGENCE_FOUNDATION_VERSION,
        "registered_modules": matrix["registry"]["modules"],
        "module_ids": matrix["registry"]["module_ids"],
        "capability_matrix": matrix,
    }


__all__ = [
    "INTELLIGENCE_FOUNDATION_VERSION",
    "IntelligenceModule",
    "IntelligenceRegistry",
    "seed_intelligence_registry",
    "select_intelligence_modules",
    "capability_matrix",
    "studio_intelligence_diagnostics",
]
