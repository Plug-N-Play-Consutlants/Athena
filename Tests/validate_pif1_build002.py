"""Validation for PIF-1 Build 002: public identity graph seed and guardrails."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Knowledge.Intelligence.Entities.entity_registry import all_entities, registry_stats
from Knowledge.Intelligence.Entities.identity_graph import graph_summary
from Knowledge.Intelligence.Routing.request_router import analyze_public_request

CASES = [
    ("Auston Matthews", "player_profile", "player_intelligence"),
    ("Austin Matthews", "player_profile", "player_intelligence"),
    ("Auston Mathtwes", "player_profile", "player_intelligence"),
    ("Compare Matthews and McDavid", "player_comparison", "player_comparison"),
    ("Who is Sebastian Aho?", "player_analysis", "disambiguate_entity"),
    ("Tell me about the Leafs", "player_analysis", "team_intelligence"),
    ("If the NHL draft were today, who goes first?", "draft_analysis", "draft_intelligence_gap"),
]


def main() -> int:
    print("PIF-1 Build 002 Validation")
    print("=" * 60)
    failures: list[str] = []

    entities = all_entities()
    stats = registry_stats()
    summary = graph_summary().to_dict()
    print(f"[INFO] entities={len(entities)} players={summary.get('player_count')} teams={summary.get('team_count')} aliases={summary.get('alias_count')}")
    if len(entities) < 18:
        failures.append(f"Expected at least 18 public seed entities, got {len(entities)}")
    if summary.get("player_count", 0) < 10:
        failures.append("Expected at least 10 public player identities")
    if "sebastian aho" not in (stats.get("ambiguous_names") or {}):
        failures.append("Sebastian Aho ambiguity is missing from registry stats")

    for question, expected_intent, expected_route in CASES:
        result = analyze_public_request(question)
        actual_intent = result.intent.intent.value
        actual_route = result.route
        ok = actual_intent == expected_intent and actual_route == expected_route
        print(f"[{'PASS' if ok else 'FAIL'}] {question!r}: intent={actual_intent}; route={actual_route}; confidence={result.confidence}")
        if not ok:
            failures.append(f"{question!r}: expected {expected_intent}/{expected_route}, got {actual_intent}/{actual_route}")

    comparison = analyze_public_request("Compare Matthews and McDavid")
    if "fantasy_owner_data" not in comparison.blocked_domains:
        failures.append("Public comparison guardrail did not block fantasy_owner_data")
    else:
        print("[PASS] public comparison blocks fantasy owner data")
    if "rulebook_knowledge" not in analyze_public_request("If the NHL draft were today, who goes first?").blocked_domains:
        failures.append("Draft guardrail did not block rulebook_knowledge")
    else:
        print("[PASS] draft guardrail blocks rulebook/CBA retrieval")

    if failures:
        print("\nOverall status: FAIL")
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1
    print("\nOverall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
