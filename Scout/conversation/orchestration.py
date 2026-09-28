"""Scout compatibility facade for Athena-owned capability handlers."""
from __future__ import annotations

from Athena.intent_planner import (
    AthenaIntentPlan as ScoutIntentPlan,
    _text, _has_any, _has_public_sports_context,
    _public_player_subjects_for, _public_player_profiles_for,
    comparison_semantics, plan_capability,
)
from Athena import capability_handlers as _handlers

ORCHESTRATION_VERSION = _handlers.ORCHESTRATION_VERSION

def scout_intent_plan(question: str, mode: str = "public"):
    """Compatibility facade for Scout callers; Athena owns the plan."""
    return plan_capability(question, mode)

_answer_player_temporal_comparison = _handlers._answer_player_temporal_comparison
_answer_player_comparison = _handlers._answer_player_comparison
_answer_ambiguous_entity = _handlers._answer_ambiguous_entity
_answer_team_window = _handlers._answer_team_window
_answer_team_projection = _handlers._answer_team_projection
_answer_player_explainability = _handlers._answer_player_explainability
_team_rows = _handlers._team_rows
_answer_fantasy_roster = _handlers._answer_fantasy_roster
_answer_trade_directions = _handlers._answer_trade_directions
_answer_draft_strategy = _handlers._answer_draft_strategy
_answer_pre_draft_context = _handlers._answer_pre_draft_context
_answer_pre_draft_branch = _handlers._answer_pre_draft_branch
_answer_rebuild_detection = _handlers._answer_rebuild_detection
_answer_contract_rule = _handlers._answer_contract_rule
_answer_public_organization_impact = _handlers._answer_public_organization_impact
_answer_longitudinal_draft = _handlers._answer_longitudinal_draft
scout_orchestrated_answer = _handlers.scout_orchestrated_answer
orchestration_diagnostics = _handlers.orchestration_diagnostics
