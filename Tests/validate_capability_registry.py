"""Validation for v0.5.6.1.0 Capability Registry Foundation."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check(name: str, condition: bool, detail: str = "") -> tuple[str, bool, str]:
    return (name, bool(condition), detail)


def version_at_least(value: str, minimum: tuple[int, int, int, int, int]) -> bool:
    try:
        return tuple(int(part) for part in value.split(".")) >= minimum
    except Exception:
        return False


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    from Core.version import ATHENA_VERSION, ATHENA_BUILD, RELEASE_NAME, VERSION_SCHEMA
    checks.append(check("athena_version", version_at_least(ATHENA_VERSION, (0, 5, 6, 1, 0)), ATHENA_VERSION))
    checks.append(check("athena_build", version_at_least(ATHENA_BUILD, (0, 5, 6, 1, 0)), ATHENA_BUILD))
    checks.append(check("release_name", bool(RELEASE_NAME), RELEASE_NAME))
    checks.append(check("version_schema", VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", VERSION_SCHEMA))

    from Core.capability_registry import capability_registry_diagnostics, seed_capability_registry
    registry = seed_capability_registry()
    caps = registry.list()
    summary = registry.summary()
    validation = registry.validate_metadata()
    graph = registry.dependency_graph()

    checks.append(check("registry_loads", registry is not None, type(registry).__name__))
    checks.append(check("discovery_succeeds", len(caps) >= 25, f"capabilities={len(caps)}"))
    checks.append(check("metadata_complete", not validation.get("missing_entrypoints"), str(validation.get("missing_entrypoints")[:5])))
    checks.append(check("dependency_graph_builds", len(graph) == len(caps), f"graph={len(graph)} caps={len(caps)}"))
    checks.append(check("knowledge_layer_present", summary.get("by_layer", {}).get("Knowledge", 0) > 0, str(summary.get("by_layer"))))
    checks.append(check("intelligence_layer_present", summary.get("by_layer", {}).get("Intelligence", 0) > 0, str(summary.get("by_layer"))))
    checks.append(check("reasoning_layer_present", summary.get("by_layer", {}).get("Reasoning", 0) > 0, str(summary.get("by_layer"))))
    checks.append(check("player_capability_present", registry.get("player_assessment") is not None, "player_assessment"))
    checks.append(check("team_capability_present", registry.get("team_assessment") is not None, "team_assessment"))
    checks.append(check("trade_capability_present", registry.get("trade_assessment") is not None, "trade_assessment"))
    checks.append(check("roster_capability_present", registry.get("roster_assessment") is not None, "roster_assessment"))
    diag = capability_registry_diagnostics(limit=5)
    checks.append(check("diagnostics_serializable", isinstance(diag, dict) and len(diag.get("capabilities", [])) <= 5, str(diag.keys())))
    checks.append(check("diagnostics_summary", diag.get("summary", {}).get("capability_count", 0) >= 25, str(diag.get("summary"))))

    failed = [c for c in checks if not c[1]]
    print("Capability Registry Validation")
    print("=" * 64)
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print("-" * 64)
    print(f"Passed: {len(checks) - len(failed)}")
    print(f"Failed: {len(failed)}")
    print(f"Overall status: {'PASS' if not failed else 'FAIL'}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
