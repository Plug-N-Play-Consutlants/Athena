"""Verify Athena owns capability planning and declares remaining fallback paths."""
from __future__ import annotations

import ast
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Athena.execution_registry import SPECIALISTS, execute_specialist
from Athena.intent_planner import plan_capability
from Athena.intent_resolution import select_executable_route
from Scout.conversation.orchestration import scout_intent_plan


def main() -> int:
    results: list[bool] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        results.append(condition)
        print(f"[{'PASS' if condition else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))

    planner = (ROOT / "Athena/intent_planner.py").read_text(encoding="utf-8")
    scout = (ROOT / "Scout/conversation/orchestration.py").read_text(encoding="utf-8")
    resolver = (ROOT / "Athena/intent_resolution.py").read_text(encoding="utf-8")
    planned = {
        node.args[0].value
        for node in ast.walk(ast.parse(planner))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        and node.func.id == "AthenaIntentPlan" and node.args
        and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)
    }
    check("all_planned_capabilities_registered", planned <= SPECIALISTS.keys(), str(sorted(planned - SPECIALISTS.keys())))
    check("athena_owns_plan", "def plan_capability(" in planner and "from Athena.intent_planner import plan_capability" in resolver and "from Scout.conversation" not in resolver)
    check("scout_compatibility_only", "return plan_capability(question, mode)" in scout and "def _public_player_subjects_for(" not in scout)

    routes = [
        ("public_comparison", "Matthews vs McKenna", "public", "public_player_comparison"),
        ("public_event", "Maple Leafs news", "public", "live_event_intelligence"),
        ("public_ambiguity", "Sebastian Aho", "public", "ambiguous_public_entity"),
        ("public_identity", "Sebastian Aho Swedish defenseman", "public", "public_player_identity"),
        ("fantasy_draft", "What should I know about the JHLPAA draft going into tomorrow?", "fantasy", "fantasy_pre_draft_context"),
        ("fantasy_history", "How has the JHLPAA draft changed over the last 10 seasons?", "fantasy", "fantasy_longitudinal_draft"),
    ]
    for label, question, mode, expected in routes:
        actual, source = select_executable_route(question, mode)
        check(label, actual == expected and actual in SPECIALISTS, f"{actual or 'fallback'} via {source}")
        planned_route = plan_capability(question, mode)
        scout_route = scout_intent_plan(question, mode)
        check(label + "_facade", getattr(planned_route, "route", None) == getattr(scout_route, "route", None))

    for label, question, mode in [
        ("legacy_manager", "Who are the most active managers?", "fantasy"),
        ("legacy_public_overview", "public sports overview", "public"),
    ]:
        actual, source = select_executable_route(question, mode)
        check(label, not actual and source == "legacy_fallback", f"{actual or 'legacy_fallback'}")

    check("public_cannot_execute_fantasy_specialist", execute_specialist("fantasy_pre_draft_context", object(), "draft", mode="public") is None)
    from Knowledge.Events.live_intelligence import _event_matches_filters
    report = {"event_type": "news", "title": "Maple Leafs players cleared waivers", "summary": "Roster report"}
    hypothetical = {"event_type": "news", "title": "Waiver player could be a fit for the Maple Leafs", "summary": "Possible target"}
    check("waiver_report_remains_selectable", _event_matches_filters(report, {"maple leafs"}, {"transaction"})[0])
    check("hypothetical_not_transaction", not _event_matches_filters(hypothetical, {"maple leafs"}, {"transaction"})[0])
    from Athena.request_execution import _continued_question
    from Knowledge.Events.live_intelligence import select_live_evidence
    followup, context_status = _continued_question(
        "What do these roster and waiver decisions imply for the opening-night roster?", "public",
        {"origin_intent": "live_event_intelligence", "subject_entity_id": "nhl.team.toronto_maple_leafs"},
    )
    with patch("Knowledge.Events.live_intelligence.acquire_live_rss_events", return_value=SimpleNamespace(events=[report, hypothetical])), patch("Knowledge.Events.live_intelligence.discover_current_news", return_value=[]):
        evidence = select_live_evidence(followup, mode="public", allow_network=True, limit=6)
    titles = [str(event.get("title") or "") for event in evidence.get("events", [])]
    check("continued_event_reaches_matching_evidence", context_status == "public_team_subject" and report["title"] in titles and hypothetical["title"] not in titles, str(titles))

    legacy_modules = sorted({spec.module for spec in SPECIALISTS.values() if spec.module.startswith("Scout.")})
    check("registered_specialists_owned_by_athena", not legacy_modules, ", ".join(legacy_modules) or "none")
    print(f"Registered specialists: {len(SPECIALISTS)}; Scout-owned executable handler modules: {', '.join(legacy_modules) or 'none'}")
    print(f"Overall status: {'PASS' if all(results) else 'FAIL'}")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
