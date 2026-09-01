"""Validate Scout Intent & Response Orchestration acceptance routing."""
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_VERSION, RELEASE_NAME
from Scout.conversation.orchestration import ORCHESTRATION_VERSION, scout_intent_plan
from Scout.conversation.router import route_question


def check(label: str, condition: bool, detail: object, failures: list[str]) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}: {detail}")
    if not condition:
        failures.append(label)


def answer(prompt: str, mode: str):
    return route_question(prompt, mode=mode)


def main() -> int:
    failures: list[str] = []
    print("Scout Intent Orchestration Validation")
    print("=" * 64)
    check("version_at_least_0_5_6_3_0", ATHENA_VERSION >= "0.5.6.3.0", ATHENA_VERSION, failures)
    check("release_name", RELEASE_NAME in {"Scout Intent Orchestration Foundation", "Scout Context Isolation Hotfix", "Workspace Runtime State Tolerance Hotfix", "Experience Layer Foundation", "Player Experience Foundation", "Player Experience Rendering Hotfix", "Player Experience Contract Hotfix", "Scout Orchestration Release Gate Hotfix", "Experience Gate Alignment Hotfix", "Player Experience Content Mapping Hotfix", "Player Experience Refinement", "Foundational Governance and Module Adaptivity", "Foundational Governance Cleanup Tolerance Hotfix", "Adaptive Investigation Strategy Foundation", "Adaptive Investigation Runtime Integration"}, RELEASE_NAME, failures)
    check("orchestration_version", ORCHESTRATION_VERSION >= "0.5.6.3.0", ORCHESTRATION_VERSION, failures)

    prompts = [
        ("public_team_window", "public", "Who are the Toronto Maple Leafs, and what will determine whether they become Stanley Cup contenders over the next three seasons?", "public_team_window_analysis"),
        ("public_comparison", "public", "Compare Connor McDavid and Nathan MacKinnon. Which player would you build a franchise around today, and why?", "public_player_comparison"),
        ("public_projection", "public", "Which NHL teams are best positioned to improve over the next three seasons?", "public_team_projection"),
        ("public_event", "public", "Explain the biggest NHL story right now and why it matters.", "live_event_intelligence"),
        ("public_explainability", "public", "Why do you believe Connor Bedard will become an elite NHL player?", "public_player_explainability"),
        ("fantasy_roster", "fantasy", "Analyze my roster and identify my biggest organizational strength and weakness.", "fantasy_roster_diagnostic"),
        ("fantasy_trade", "fantasy", "Recommend three realistic trade directions for my team and explain why each benefits both managers.", "fantasy_trade_directions"),
        ("fantasy_trade_target_type", "fantasy", "Looking at my league, what type of player should I target in a trade rather than which specific player?", "fantasy_trade_directions"),
        ("fantasy_draft", "fantasy", "I have the 8th overall pick. Should I draft for upside or organizational need?", "fantasy_draft_strategy"),
        ("fantasy_rebuild", "fantasy", "Which managers in my league appear to be entering a rebuild, and what evidence supports that conclusion?", "fantasy_rebuild_detection"),
        ("fantasy_contract_rule", "fantasy", "If I trade for a player whose contract expires in 2027, what happens to that contract in our league?", "fantasy_contract_rule"),
        ("aho_ambiguity", "fantasy", "Tell me about Sebastian Aho.", "public_entity_disambiguation"),
    ]
    for label, mode, prompt, expected_intent in prompts:
        result = answer(prompt, mode)
        check(label, result.get("intent") == expected_intent, f"intent={result.get('intent')} expected={expected_intent}; title={result.get('title')}", failures)
        text = str(result.get("natural_language_response") or "")
        check(f"{label}_has_public_text", len(text) > 80, text[:120], failures)

    aho = answer("Tell me about Sebastian Aho.", "public")
    check("aho_cards_available", len(aho.get("cards") or []) >= 2, aho.get("cards"), failures)
    mckenna_public_after_fantasy = answer("The Toronto Maple Leafs selected Gavin McKenna first overall in the 2026 NHL Draft. Evaluate how that decision changes the organization's outlook over the next five years.", "fantasy")
    check("public_prompt_overrides_fantasy_mode", mckenna_public_after_fantasy.get("intent") == "public_organization_impact", f"intent={mckenna_public_after_fantasy.get('intent')}; title={mckenna_public_after_fantasy.get('title')}", failures)

    comparison = answer("Compare Connor McDavid and Nathan MacKinnon. Which player would you build a franchise around today, and why?", "public")
    check("comparison_not_live_event", comparison.get("intent") != "live_event_intelligence", comparison.get("intent"), failures)
    draft = answer("I have the 8th overall pick. Should I draft for upside or organizational need?", "fantasy")
    check("draft_not_clarify", draft.get("intent") != "clarify_or_help", draft.get("intent"), failures)
    contract = answer("If I trade for a player whose contract expires in 2027, what happens to that contract in our league?", "fantasy")
    check("contract_explains_expiry_year", "expiry year" in str(contract.get("natural_language_response", "")).lower(), contract.get("natural_language_response", "")[:160], failures)
    plan = scout_intent_plan("Compare Connor McDavid and Nathan MacKinnon. Which player would you build a franchise around today, and why?", "public")
    check("comparison_plan_priority", plan is not None and plan.route == "public_player_comparison" and plan.priority >= 90, plan, failures)

    print("-" * 64)
    if failures:
        print("Overall status: FAIL")
        print(f"Failed: {len(failures)}")
        return 1
    print("Overall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
