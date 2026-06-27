"""Doctor checks for PIF-1 Build 002."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CHECKS = [
    "Knowledge.Intelligence.Intent.intent_types",
    "Knowledge.Intelligence.Intent.intent_classifier",
    "Knowledge.Intelligence.Entities.entity_registry",
    "Knowledge.Intelligence.Entities.entity_extractor",
    "Knowledge.Intelligence.Entities.fuzzy_match",
    "Knowledge.Intelligence.Entities.disambiguation",
    "Knowledge.Intelligence.Entities.identity_graph",
    "Knowledge.Intelligence.Routing.request_router",
]


def main() -> int:
    print("PIF-1 Build 002 Doctor")
    print("=" * 60)
    failures: list[str] = []
    for module_name in CHECKS:
        try:
            module = importlib.import_module(module_name)
            print(f"[PASS] import: {module_name} -> {getattr(module, '__file__', 'unknown')}")
        except Exception as exc:
            print(f"[FAIL] import: {module_name}: {exc}")
            failures.append(module_name)

    try:
        from Knowledge.Intelligence.Entities.entity_registry import all_entities, registry_stats
        from Knowledge.Intelligence.Entities.identity_graph import graph_summary
        entities = all_entities()
        stats = registry_stats()
        summary = graph_summary().to_dict()
        print(f"[PASS] registry loaded: {len(entities)} entities")
        print(f"[PASS] identity graph summary: {summary}")
        if len(entities) < 18:
            failures.append("entity_count")
        if "sebastian aho" not in (stats.get("ambiguous_names") or {}):
            failures.append("sebastian_aho_ambiguity")
    except Exception as exc:
        print(f"[FAIL] identity graph inspection: {exc}")
        failures.append("identity_graph_inspection")

    try:
        from Knowledge.Intelligence.Routing.request_router import analyze_public_request
        probes = {
            "Compare Matthews and McDavid": "player_comparison",
            "Who is Sebastian Aho?": "disambiguate_entity",
            "If the NHL draft were today, who goes first?": "draft_intelligence_gap",
        }
        for question, expected_route in probes.items():
            result = analyze_public_request(question)
            if result.route == expected_route:
                print(f"[PASS] route probe: {question!r} -> {result.route}")
            else:
                print(f"[FAIL] route probe: {question!r} -> {result.route}, expected {expected_route}")
                failures.append(question)
    except Exception as exc:
        print(f"[FAIL] routing probes: {exc}")
        failures.append("routing_probes")

    if failures:
        print("\nOverall status: FAIL")
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1
    print("\nOverall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
