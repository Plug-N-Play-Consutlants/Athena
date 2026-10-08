"""System-wide Athena application-path ownership trace.

This is diagnostic infrastructure, not a feature surface. It records who owns
routing, acquisition, normalization, specialist execution and presentation for
major evidence domains so cleanup can target structural exceptions explicitly.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def build_trace() -> dict[str, Any]:
    from Athena.execution_registry import SPECIALISTS
    from Athena.intent_resolution import select_executable_route

    specialist_owners = {route: spec.module for route, spec in sorted(SPECIALISTS.items())}
    scout_owned = {route: module for route, module in specialist_owners.items() if module.startswith("Scout.")}
    cases = [
        {
            "domain": "player_identity_and_stats",
            "question": "How has Connor McDavid's NHL performance changed over the last 3 seasons?",
            "mode": "public",
            "expected_route": "public_player_temporal_comparison",
            "acquisition_owner": "Athena.request_execution",
            "normalization_owner": "Knowledge.Intelligence.Public.player_evidence",
            "authority": "canonical_player_statistical_evidence",
        },
        {
            "domain": "current_news_events",
            "question": "Maple Leafs news",
            "mode": "public",
            "expected_route": "live_event_intelligence",
            "acquisition_owner": "Knowledge.Events.live_intelligence",
            "normalization_owner": "Knowledge.Events",
            "authority": "normalized_event_evidence",
        },
        {
            "domain": "rules_and_cap_boundary",
            "question": "Maple Leafs salary cap usage this year",
            "mode": "public",
            "expected_route": "public_nhl_cap_reasoning",
            "acquisition_owner": "Athena.request_execution",
            "normalization_owner": "Reasoning.Cap.cap_reasoning",
            "authority": "bounded_team_economic_state_incomplete_ledger",
        },
        {
            "domain": "historical_fantasy",
            "question": "What can you tell me about how the JHLPAA draft has changed over the last 10 seasons?",
            "mode": "fantasy",
            "expected_route": "fantasy_longitudinal_draft",
            "acquisition_owner": "Knowledge.LeagueHistory.evidence_registry",
            "normalization_owner": "Knowledge.Intelligence.Fantasy.historical_draft",
            "authority": "canonical_historical_draft_evidence",
        },
    ]
    for case in cases:
        route, selected_by = select_executable_route(case["question"], case["mode"])
        case["actual_route"] = route
        case["selected_by"] = selected_by
        case["route_matches"] = route == case["expected_route"]
        case["specialist_module"] = specialist_owners.get(route, "legacy_fallback") if route else "legacy_fallback"

    unresolved = []
    if scout_owned:
        unresolved.append({
            "id": "scout_specialist_implementation_ownership",
            "severity": "structural",
            "status": "correction_required",
            "detail": "Executable Athena specialists still implemented in Scout modules.",
            "routes": scout_owned,
        })
    unresolved.append({
        "id": "current_public_cap_ledger",
        "severity": "evidence_gap",
        "status": "known_unregistered",
        "detail": "Bounded team state is registered, but a complete current public payroll/roster cap ledger and adjustment ledger are not yet registered.",
    })
    return {
        "contract": "athena_application_path_trace",
        "trace_scope": [case["domain"] for case in cases],
        "cases": cases,
        "specialist_owners": specialist_owners,
        "unresolved": unresolved,
        "structural_corrections_required": sum(1 for item in unresolved if item["status"] == "correction_required"),
        "route_failures": [case["domain"] for case in cases if not case["route_matches"]],
    }


def main() -> int:
    trace = build_trace()
    print("Athena Application Path Trace")
    print("=" * 64)
    for case in trace["cases"]:
        state = "PASS" if case["route_matches"] else "FAIL"
        print(f"[{state}] {case['domain']}: {case['actual_route'] or 'legacy_fallback'} via {case['selected_by']}")
        print(f"       specialist={case['specialist_module']}; acquisition={case['acquisition_owner']}; authority={case['authority']}")
    for item in trace["unresolved"]:
        print(f"[TRACE] {item['id']}: {item['status']} - {item['detail']}")
    print(f"Structural corrections required: {trace['structural_corrections_required']}")
    print(f"Route failures: {len(trace['route_failures'])}")
    return 1 if trace["route_failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
