"""Doctor checks for PIF-1 Build 001."""

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
    "Knowledge.Intelligence.Routing.request_router",
]


def main() -> int:
    print("PIF-1 Build 001 Doctor")
    print("=" * 52)
    failures = []
    for module_name in CHECKS:
        try:
            module = importlib.import_module(module_name)
            print(f"[PASS] import: {module_name} -> {getattr(module, '__file__', 'unknown')}")
        except Exception as exc:
            print(f"[FAIL] import: {module_name}: {exc}")
            failures.append(module_name)

    try:
        from Knowledge.Intelligence.Entities.entity_registry import all_entities
        entities = all_entities()
        print(f"[PASS] seed entities: {len(entities)} registered")
        aho = [entity for entity in entities if entity.canonical_name == "Sebastian Aho"]
        if len(aho) == 2:
            print("[PASS] ambiguous entity seed: Sebastian Aho has two distinct entities")
        else:
            print(f"[FAIL] ambiguous entity seed: expected 2 Sebastian Aho entities, got {len(aho)}")
            failures.append("sebastian_aho_seed")
    except Exception as exc:
        print(f"[FAIL] entity seed inspection: {exc}")
        failures.append("entity_seed_inspection")

    try:
        from Knowledge.Intelligence.Routing.request_router import analyze_public_request
        result = analyze_public_request("Who is Sebastian Aho?")
        if result.route == "disambiguate_entity":
            print("[PASS] disambiguation route: Who is Sebastian Aho? -> disambiguate_entity")
        else:
            print(f"[FAIL] disambiguation route: got {result.route}")
            failures.append("disambiguation_route")
    except Exception as exc:
        print(f"[FAIL] routing probe: {exc}")
        failures.append("routing_probe")

    if failures:
        print("\nOverall status: FAIL")
        return 1
    print("\nOverall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
