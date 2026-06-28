"""Validation for v0.5.6.0.0 Intent Classification Foundation."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def record(results: list[tuple[str, bool, str]], name: str, condition: bool, detail: str = "") -> None:
    results.append((name, bool(condition), detail))


def main() -> int:
    results: list[tuple[str, bool, str]] = []

    from Core.version import ATHENA_VERSION, ATHENA_BUILD, RELEASE_NAME
    from Intelligence.Orchestration import (
        INTENT_FOUNDATION_VERSION,
        EXECUTION_PLANNER_VERSION,
        DEVELOPER_TRACE_VERSION,
        IntentType,
        build_execution_plan,
        build_orchestration_trace,
        classify_request_intent,
        orchestration_diagnostics,
        taxonomy_diagnostics,
    )

    record(results, "athena_version", ATHENA_VERSION == "0.5.6.0.0", ATHENA_VERSION)
    record(results, "athena_build", ATHENA_BUILD == "0.5.6.0.0", ATHENA_BUILD)
    record(results, "release_name", "Intent Classification Foundation" in RELEASE_NAME, RELEASE_NAME)
    record(results, "intent_foundation_version", INTENT_FOUNDATION_VERSION == "0.5.6.0.0", INTENT_FOUNDATION_VERSION)
    record(results, "execution_planner_version", EXECUTION_PLANNER_VERSION == "0.5.6.0.0", EXECUTION_PLANNER_VERSION)
    record(results, "developer_trace_version", DEVELOPER_TRACE_VERSION == "0.5.6.0.0", DEVELOPER_TRACE_VERSION)

    taxonomy = taxonomy_diagnostics()
    record(results, "taxonomy_count", taxonomy.get("intent_count", 0) >= 10, str(taxonomy.get("intent_count")))
    record(results, "taxonomy_has_impact", "impact" in taxonomy.get("families", {}), str(taxonomy.get("families")))

    cases = [
        ("Tell me about Auston Matthews.", IntentType.PLAYER_PROFILE),
        ("Tell me about the Toronto Maple Leafs.", IntentType.TEAM_PROFILE),
        ("Matthews vs McDavid", IntentType.PLAYER_COMPARISON),
        ("How does Gavin McKenna improve the Leafs?", IntentType.ORGANIZATIONAL_IMPACT),
        ("Detroit weaknesses", IntentType.ROSTER_CONSTRUCTION),
        ("Why are the Leafs disappointing?", IntentType.CAUSAL_EXPLANATION),
        ("Should I trade Matthews in my Fantrax league?", IntentType.FANTASY_TRADE_ANALYSIS),
    ]

    for question, expected in cases:
        classified = classify_request_intent(question, mode="fantasy" if "Fantrax" in question else "public")
        record(results, f"intent:{question[:28]}", classified.primary_intent == expected, f"expected={expected.value}; actual={classified.primary_intent.value}; confidence={classified.confidence}")

    impact_plan = build_execution_plan("How does Gavin McKenna improve the Leafs?", mode="public")
    domains = [step.capability_domain for step in impact_plan.steps]
    record(results, "impact_plan_template", impact_plan.composition_template == "organizational_impact_brief", impact_plan.composition_template)
    record(results, "impact_plan_includes_player", "player_intelligence" in domains, str(domains))
    record(results, "impact_plan_includes_team", "team_intelligence" in domains, str(domains))
    record(results, "impact_plan_includes_reasoning", "reasoning" in domains, str(domains))
    record(results, "impact_plan_entities_not_destination", any("Entities are planning inputs" in note for note in impact_plan.notes), str(impact_plan.notes))

    trace = build_orchestration_trace("Matthews vs McDavid", mode="public").to_dict()
    record(results, "trace_visibility", trace.get("visibility") == "developer_only", str(trace.get("visibility")))
    record(results, "trace_has_intent", trace.get("intent", {}).get("primary_intent") == "player_comparison", str(trace.get("intent")))
    record(results, "trace_has_selected_capabilities", len(trace.get("capabilities_selected", [])) >= 2, str(trace.get("capabilities_selected")))
    record(results, "trace_has_template", bool(trace.get("composition_template")), str(trace.get("composition_template")))

    diag = orchestration_diagnostics()
    record(results, "diagnostics_panel", diag.get("panel") == "intent_classification_foundation", str(diag.get("panel")))
    record(results, "diagnostics_samples", diag.get("sample_count") == 4, str(diag.get("sample_count")))
    record(results, "diagnostics_public_hidden", diag.get("public_visibility") == "hidden", str(diag.get("public_visibility")))

    failed = [item for item in results if not item[1]]
    print("Intent Classification Foundation Validation")
    print("=" * 64)
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"\nOverall status: {'PASS' if not failed else 'FAIL'}")
    print(f"Passed: {len(results) - len(failed)}")
    print(f"Failed: {len(failed)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
