"""Executable specialist registry for Athena's question path.

Registration means the handler can be resolved and called. It does not imply
that live evidence, current provider data, or a full answer is available.
"""
from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any, Dict


@dataclass(frozen=True)
class Specialist:
    route: str
    module: str
    function: str
    mode: str


_ORCHESTRATION = "Athena.capability_handlers"
_LIVE = "Athena.live_event_specialist"
SPECIALISTS: Dict[str, Specialist] = {
    route: Specialist(route, _ORCHESTRATION, function, mode)
    for route, function, mode in (
        ("public_player_temporal_comparison", "_answer_player_temporal_comparison", "public"),
        ("public_player_comparison", "_answer_player_comparison", "public"),
        ("ambiguous_public_entity", "_answer_ambiguous_entity", "public"),
        ("public_team_window", "_answer_team_window", "public"),
        ("public_team_projection", "_answer_team_projection", "public"),
        ("public_player_explainability", "_answer_player_explainability", "public"),
        ("public_organization_impact", "_answer_public_organization_impact", "public"),
        ("public_nhl_economic_context", "_answer_nhl_economic_context", "public"),
        ("public_nhl_team_economic_state", "_answer_nhl_team_economic_state", "public"),
        ("public_nhl_cap_reasoning", "_answer_nhl_cap_reasoning", "public"),
        ("public_nhl_transaction_scenario", "_answer_nhl_transaction_scenario", "public"),
        ("public_nhl_organizational_assets", "_answer_nhl_organizational_assets", "public"),
        ("public_nhl_organizational_plausibility", "_answer_nhl_organizational_plausibility", "public"),
        ("public_nhl_player_contract", "_answer_nhl_player_contract", "public"),
        ("public_nhl_player_asset_state", "_answer_nhl_player_asset_state", "public"),
        ("fantasy_longitudinal_draft", "_answer_longitudinal_draft", "fantasy"),
        ("fantasy_pre_draft_context", "_answer_pre_draft_context", "fantasy"),
        ("fantasy_roster_diagnostic", "_answer_fantasy_roster", "fantasy"),
        ("fantasy_trade_directions", "_answer_trade_directions", "fantasy"),
        ("fantasy_draft_strategy", "_answer_draft_strategy", "fantasy"),
        ("fantasy_rebuild_detection", "_answer_rebuild_detection", "fantasy"),
        ("fantasy_contract_rule", "_answer_contract_rule", "fantasy"),
    )
}
for _route in ("fantasy_keeper_pool_context", "fantasy_draft_capital_context", "fantasy_historical_draft_context"):
    SPECIALISTS[_route] = Specialist(_route, _ORCHESTRATION, "_answer_pre_draft_branch", "fantasy")
SPECIALISTS["live_event_intelligence"] = Specialist("live_event_intelligence", _LIVE, "_live_events_answer", "public")
SPECIALISTS["public_player_identity"] = Specialist("public_player_identity", "Athena.public_identity", "execute_public_player", "public")
SPECIALISTS["public_player_development"] = Specialist("public_player_development", "Athena.player_development", "execute_player_development", "public")
SPECIALISTS["public_player_investigation"] = Specialist("public_player_investigation", "Athena.public_identity", "execute_public_player_investigation", "public")


def execute_specialist(route: str, context: Any, question: str, *, mode: str) -> Dict[str, Any] | None:
    spec = SPECIALISTS.get(str(route or ""))
    if spec is None:
        return None
    # The route is a bounded execution contract, not a broad module scan.
    if spec.mode == "fantasy" and mode != "fantasy":
        return None
    handler = getattr(import_module(spec.module), spec.function)
    if spec.function == "_answer_pre_draft_branch":
        return handler(context, question, spec.route)
    if spec.function == "_live_events_answer":
        return handler(context, question, mode)
    return handler(context, question)
