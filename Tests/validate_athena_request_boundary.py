"""Validate the active request seam without invoking network specialists."""
from __future__ import annotations

import ast
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.version import ATHENA_VERSION


def main() -> int:
    # Load the contract without importing Athena's provider connection package.
    package = types.ModuleType("Athena")
    package.__path__ = [str(ROOT / "Athena")]
    original_package = sys.modules.get("Athena")
    sys.modules["Athena"] = package
    spec = importlib.util.spec_from_file_location("Athena.request_execution", ROOT / "Athena/request_execution.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    AthenaRequest, execute_request = module.AthenaRequest, module.execute_request

    checks: list[tuple[str, bool]] = []
    def check(name: str, ok: bool) -> None:
        checks.append((name, ok))
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")

    app = (ROOT / "Scout/app.py").read_text(encoding="utf-8")
    ask_endpoint = app.split('if path == "/api/ask":', 1)[1].split('if path in {"/api/sync"', 1)[0]
    check("scout_asks_athena", "Athena.ask(question_text" in ask_endpoint and "route_question(" not in ask_endpoint)
    orchestrator = ast.parse((ROOT / "Athena/orchestrator.py").read_text(encoding="utf-8"))
    ask_methods = [node for node in ast.walk(orchestrator) if isinstance(node, ast.FunctionDef) and node.name == "ask"]
    check("athena_ask_executes_request", len(ask_methods) >= 2 and any("execute_request(request)" in ast.unparse(node) for node in ask_methods))

    ctx = object()
    specialist_answer = {"intent": "specialist_test", "public_comment": "Final visible answer", "developer": {"source": "test"}}
    with patch("Athena.intent_resolution.select_executable_route", return_value=("", "legacy_fallback")), patch("Athena.specialist_compatibility.execute_existing_specialist", return_value=specialist_answer) as adapter:
        answer = execute_request(AthenaRequest("a question", mode="public", context=ctx, sections=("rules",)))
        adapter.assert_called_once_with("a question", mode="public", context=ctx)
    check("answer_preserved", answer["public_comment"] == "Final visible answer")
    execution = answer["developer"]["athena_request"]
    check("boundary_recorded", execution["boundary"] == "Athena.ask" and execution["version"] == ATHENA_VERSION)
    check("delegation_honest", execution["execution_owner"] == "legacy_scout_specialist_adapter")
    check("direction_recorded", execution["mode"] == "public" and execution["requested_sections"] == ["rules"])

    registered_answer = {"intent": "fantasy_longitudinal_draft", "public_comment": "10 seasons", "developer": {}}
    with patch("Athena.intent_resolution.select_executable_route", return_value=("fantasy_longitudinal_draft", "scout_intent_plan")), patch("Athena.execution_registry.execute_specialist", return_value=registered_answer) as handler, patch("Athena.specialist_compatibility.execute_existing_specialist") as fallback:
        dispatched = execute_request(AthenaRequest("draft history", mode="fantasy", context=ctx))
        handler.assert_called_once_with("fantasy_longitudinal_draft", ctx, "draft history", mode="fantasy")
        check("registered_dispatch_without_fallback", not fallback.called and dispatched["developer"]["athena_request"]["execution_owner"] == "athena_registered_specialist")
    from Athena.execution_registry import SPECIALISTS
    check("operational_routes_registered", {"public_player_comparison", "public_player_investigation", "live_event_intelligence", "fantasy_pre_draft_context", "fantasy_longitudinal_draft"}.issubset(SPECIALISTS))
    from Athena.intent_resolution import select_executable_route
    for label, prompt, mode, expected in (
        ("comparison_route", "Auston Matthews vs Connor McDavid", "public", "public_player_comparison"),
        ("live_route", "What's the latest Maple Leafs news?", "public", "live_event_intelligence"),
        ("pre_draft_route", "What does the current JHLPAA roster snapshot tell us about the upcoming draft pool?", "fantasy", "fantasy_pre_draft_context"),
        ("historical_route", "How has the JHLPAA draft changed over the last 10 seasons?", "fantasy", "fantasy_longitudinal_draft"),
    ):
        route, _ = select_executable_route(prompt, mode)
        check(label, route == expected)
    from Athena.intent_planner import plan_capability
    from Scout.conversation.orchestration import scout_intent_plan
    check("athena_planner_owns_specialist_selection", select_executable_route("Auston Matthews vs Connor McDavid", "public")[1] == "athena_intent_plan")
    check("scout_planner_is_compatibility_facade", scout_intent_plan("Analyze my roster and identify strengths", "fantasy") == plan_capability("Analyze my roster and identify strengths", "fantasy"))
    from Athena.request_execution import _continued_question
    from Knowledge.Intelligence.Entities.entity_extractor import resolve_qualified_player
    qualified = resolve_qualified_player("Sebastian Aho Swedish defenseman")
    check("qualified_public_identity", qualified is not None and qualified.entity is not None and qualified.entity.entity_id == "nhl.player.sebastian_aho_swe" and select_executable_route("Sebastian Aho Swedish defenseman", "public")[0] == "public_player_identity")
    conflicting = resolve_qualified_player("Sebastian Aho Swedish center")
    check("conflicting_qualifiers_bounded", conflicting is not None and conflicting.entity is None and select_executable_route("Sebastian Aho Swedish center", "public")[0] == "public_player_identity")
    continued, status = _continued_question("What do these roster and waiver decisions imply for the opening-night roster?", "public", {"origin_intent": "live_event_intelligence", "subject_entity_id": "nhl.team.toronto_maple_leafs"})
    check("followup_subject_preserved", status == "public_team_subject" and "Toronto Maple Leafs" in continued and select_executable_route(continued, "public")[0] == "live_event_intelligence")
    generated_followup, generated_status = _continued_question("What is changing in the team's system and player roles, and what evidence supports it?", "public", {"origin_intent": "live_event_intelligence", "subject_entity_id": "nhl.team.toronto_maple_leafs"})
    check("generated_news_followup_preserves_subject", generated_status == "public_team_subject" and "Toronto Maple Leafs" in generated_followup and select_executable_route(generated_followup, "public")[0] == "live_event_intelligence")
    check("unrelated_question_does_not_inherit_subject", _continued_question("What is hockey?", "public", {"origin_intent": "live_event_intelligence", "subject_entity_id": "nhl.team.toronto_maple_leafs"})[0] == "What is hockey?")
    from Knowledge.Events.live_intelligence import _event_matches_filters
    waiver = {"title": "A team player cleared waivers", "summary": "Roster move", "event_type": "news"}
    speculative = {"title": "A veteran hits waivers and is a fit for a team", "summary": "Potential claim", "event_type": "news"}
    check("reported_waiver_news_selectable", _event_matches_filters(waiver, set(), {"transaction"})[0])
    check("speculation_not_transaction_evidence", not _event_matches_filters(speculative, set(), {"transaction"})[0])
    player_continuation = {"origin_intent": "public_player_profile", "subject_entity_id": "nhl.player.sebastian_aho_swe"}
    player_followup, player_status = _continued_question("What are the biggest evidence-backed uncertainties in Sebastian Aho's outlook?", "public", player_continuation)
    check("player_followup_qualified", player_status == "public_player_subject" and resolve_qualified_player(player_followup).entity.entity_id == player_continuation["subject_entity_id"])
    from types import SimpleNamespace
    swedish = execute_request(AthenaRequest("Sebastian Aho Swedish defenseman", mode="public", context=SimpleNamespace(files_loaded=[])))
    check("public_profile_identity_bound", swedish.get("intent") == "public_player_profile" and swedish.get("continuation", {}).get("subject_entity_id") == player_continuation["subject_entity_id"] and "80 points" not in swedish.get("public_comment", "") and "Top 50 Players" not in " ".join(swedish.get("observed_facts", [])))
    continued_player = execute_request(AthenaRequest("What are the biggest evidence-backed uncertainties in Sebastian Aho's outlook?", mode="public", context=SimpleNamespace(files_loaded=[]), continuation=player_continuation))
    check("player_followup_reaches_question_reasoning", continued_player.get("intent") == "public_player_investigation" and continued_player.get("developer", {}).get("athena_request", {}).get("selected_by") == "continued_public_identity" and continued_player.get("developer", {}).get("identity_resolution", {}).get("entity", {}).get("entity_id") == player_continuation["subject_entity_id"] and "uncertainty" in continued_player.get("title", "") and continued_player.get("public_comment") != swedish.get("public_comment"))
    development = execute_request(AthenaRequest("What does Sebastian Aho's developmental track suggest about his NHL transition?", mode="public", context=SimpleNamespace(files_loaded=[]), continuation=player_continuation))
    check("development_followup_uses_question", development.get("intent") == "public_player_investigation" and "development" in development.get("title", "") and "current NHL role" in development.get("public_comment", ""))
    roster = execute_request(AthenaRequest("How does Sebastian Aho fit into the current roster?", mode="public", context=SimpleNamespace(files_loaded=[]), continuation=player_continuation))
    check("roster_followup_uses_question", roster.get("intent") == "public_player_investigation" and "organizational fit" in roster.get("title", ""))
    check("client_continuation_seam", 'continuation: answer.continuation' in app and 'continuation=body.get("continuation")' in ask_endpoint)
    for module_name in {spec.module for spec in SPECIALISTS.values()}:
        path = ROOT / (module_name.replace(".", "/") + ".py")
        declared = {node.name for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))) if isinstance(node, ast.FunctionDef)}
        check(f"handler_contract:{module_name}", all(spec.function in declared for spec in SPECIALISTS.values() if spec.module == module_name))

    try:
        execute_request(AthenaRequest("query", mode="invalid"))
        invalid_mode_rejected = False
    except ValueError:
        invalid_mode_rejected = True
    check("invalid_mode_rejected", invalid_mode_rejected)
    sys.modules.pop("Athena.request_execution", None)
    if original_package is None:
        sys.modules.pop("Athena", None)
    else:
        sys.modules["Athena"] = original_package
    passed = all(ok for _, ok in checks)
    print(f"Overall status: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
