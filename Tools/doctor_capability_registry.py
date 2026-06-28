"""Doctor for v0.5.6.1.0 Capability Registry Foundation."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check(name: str, condition: bool, detail: str = "") -> tuple[str, bool, str]:
    return (name, bool(condition), detail)


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    try:
        from Core.version import ATHENA_VERSION, ATHENA_BUILD, RELEASE_NAME, VERSION_SCHEMA
        checks.append(check("version_at_least_0_5_6_1_0", tuple(map(int, ATHENA_VERSION.split('.'))) >= (0,5,6,1,0), ATHENA_VERSION))
        checks.append(check("athena_build", ATHENA_BUILD == ATHENA_VERSION, ATHENA_BUILD))
        checks.append(check("release_name_available", bool(RELEASE_NAME), RELEASE_NAME))
        checks.append(check("version_schema_locked", VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", VERSION_SCHEMA))
    except Exception as exc:
        checks.append(check("version_import", False, str(exc)))

    required = [
        "Core/capability_registry.py",
        "Tools/doctor_capability_registry.py",
        "Tests/validate_capability_registry.py",
    ]
    for rel in required:
        checks.append(check(f"required_file:{rel}", (ROOT / rel).exists(), rel))

    try:
        from Core.capability_registry import CAPABILITY_REGISTRY_VERSION, capability_registry_diagnostics, seed_capability_registry
        registry = seed_capability_registry()
        capabilities = registry.list()
        summary = registry.summary()
        validation = registry.validate_metadata()
        checks.append(check("registry_version", CAPABILITY_REGISTRY_VERSION == "0.5.6.1.0", CAPABILITY_REGISTRY_VERSION))
        checks.append(check("capabilities_discovered", len(capabilities) >= 25, str(len(capabilities))))
        checks.append(check("core_layers_discovered", {"Knowledge", "Intelligence", "Reasoning"}.issubset(set(summary.get("by_layer", {}))), str(summary.get("by_layer"))))
        checks.append(check("foundation_modules_registered", any(c.capability_id == "player_assessment" for c in capabilities), "player_assessment"))
        checks.append(check("team_assessment_registered", any(c.capability_id == "team_assessment" for c in capabilities), "team_assessment"))
        checks.append(check("trade_assessment_registered", any(c.capability_id == "trade_assessment" for c in capabilities), "trade_assessment"))
        checks.append(check("dependency_graph_available", bool(registry.dependency_graph()), str(len(registry.dependency_graph()))))
        checks.append(check("no_duplicate_capability_ids", not validation.get("duplicate_ids"), str(validation.get("duplicate_ids"))))
        checks.append(check("no_missing_entrypoints", not validation.get("missing_entrypoints"), str(validation.get("missing_entrypoints")[:5])))
        diag = capability_registry_diagnostics()
        checks.append(check("studio_diagnostics_payload", diag.get("panel") == "capability_registry", str(diag.get("summary", {}).get("status"))))
    except Exception as exc:
        checks.append(check("capability_registry_import", False, f"{type(exc).__name__}: {exc}"))

    failed = [c for c in checks if not c[1]]
    print("Capability Registry Doctor")
    print("=" * 64)
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"\nOverall status: {'PASS' if not failed else 'FAIL'}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
