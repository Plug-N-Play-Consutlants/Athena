"""Adaptive investigation planning foundation.

This orchestrator coordinates contracts; it intentionally does not execute legacy
Scout routes yet. Existing output behavior remains untouched in v0.6.4.1.0.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Tuple
from Intelligence.Foundation.module_contracts import ModuleContractRegistry, seed_module_contract_registry
from .strategy import InvestigationStrategy, select_investigation_strategy
from .context_policy import ContextPolicy
from .composition_contract import CompositionContract

@dataclass(frozen=True)
class InvestigationPlan:
    intent: str
    strategy: InvestigationStrategy
    domain: str
    capability_resolution: Dict[str, Tuple[str, ...]]
    unresolved_capabilities: Tuple[str, ...]
    context_policy: ContextPolicy
    composition: CompositionContract
    create_working_state: bool

    def to_dict(self) -> dict:
        return {
            "version": "0.6.4.1.0", "intent": self.intent, "strategy": self.strategy.to_dict(), "domain": self.domain,
            "capability_resolution": self.capability_resolution, "unresolved_capabilities": self.unresolved_capabilities,
            "context_policy": {k: int(v) for k,v in self.context_policy.priorities.items()},
            "composition": asdict(self.composition), "create_working_state": self.create_working_state,
        }

def build_investigation_plan(intent: str, *, domain: str = "all", module_registry: ModuleContractRegistry | None = None) -> InvestigationPlan:
    strategy = select_investigation_strategy(intent)
    registry = module_registry or seed_module_contract_registry()
    resolution = registry.resolve_capabilities(strategy.requested_capabilities, domain)
    unresolved = tuple(cap for cap, modules in resolution.items() if not modules)
    return InvestigationPlan(
        intent=intent, strategy=strategy, domain=domain, capability_resolution=resolution,
        unresolved_capabilities=unresolved, context_policy=ContextPolicy.for_strategy(strategy.strategy_id),
        composition=CompositionContract.from_strategy(strategy), create_working_state=strategy.maintain_working_state,
    )

def investigation_diagnostics() -> dict:
    samples = {}
    for intent in ("score_update", "live_event_intelligence", "public_player_profile", "public_player_comparison", "public_team_window_analysis", "fantasy_trade_directions"):
        plan = build_investigation_plan(intent)
        samples[intent] = {"strategy": plan.strategy.strategy_id, "depth": plan.strategy.depth, "state": plan.create_working_state, "composition": plan.composition.profile, "unresolved": plan.unresolved_capabilities}
    rich = samples["public_player_comparison"]["depth"] == "rich" and samples["public_player_profile"]["depth"] == "rich"
    brief = samples["score_update"]["depth"] == "concise" and samples["live_event_intelligence"]["depth"] == "concise"
    return {"version": "0.6.4.1.0", "status": "pass" if rich and brief else "fail", "adaptive_depth": True, "preserves_rich_experiences": rich, "brief_updates": brief, "samples": samples}
