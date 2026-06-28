"""Doctor for v0.5.5.5.26 Consensus Repository Cleanup."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _version_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.split("."))


def check(name: str, condition: bool, detail: str = "") -> tuple[str, bool, str]:
    return name, bool(condition), detail


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    try:
        from Core.version import (
            ATHENA_BUILD,
            ATHENA_VERSION,
            RELEASE_EPIC,
            RELEASE_HOTFIX,
            RELEASE_NAME,
            RELEASE_PATCH,
            RELEASE_SPRINT,
            SCOUT_VERSION,
            VERSION,
            VERSION_SCHEMA,
        )
        checks.append(check("version_advanced", _version_tuple(ATHENA_VERSION) >= (0, 5, 5, 5, 26), ATHENA_VERSION))
        checks.append(check("build_matches_version", ATHENA_BUILD == ATHENA_VERSION, f"{ATHENA_BUILD} / {ATHENA_VERSION}"))
        checks.append(check("scout_matches_version", SCOUT_VERSION == f"v{ATHENA_VERSION}", SCOUT_VERSION))
        checks.append(check("compat_version_alias", VERSION == ATHENA_VERSION, VERSION))
        checks.append(check("schema_locked", VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", VERSION_SCHEMA))
        checks.append(check("release_name_available", bool(RELEASE_NAME), RELEASE_NAME))
        checks.append(check("release_metadata_alignment", RELEASE_NAME == "Consensus Repository Cleanup", RELEASE_NAME))
        checks.append(check("release_fields", (RELEASE_EPIC, RELEASE_SPRINT, RELEASE_PATCH, RELEASE_HOTFIX) == ("5", "5", "5", "26"), f"{RELEASE_EPIC}.{RELEASE_SPRINT}.{RELEASE_PATCH}.{RELEASE_HOTFIX}"))
    except Exception as exc:
        checks.append(check("core_version_import", False, f"{type(exc).__name__}: {exc}"))

    legacy_core = ROOT / "Intelligence" / "Core"
    checks.append(check("legacy_intelligence_core_removed", not legacy_core.exists(), str(legacy_core)))

    for rel in [
        "Tools/doctor_runtime_orchestration_observability.py",
        "Tools/doctor_scout_runtime_acceptance_hotfix.py",
        "Tools/doctor_live_event_source_integration.py",
        "Tests/validate_runtime_orchestration_observability.py",
        "Tests/validate_scout_runtime_acceptance_hotfix.py",
        "Tests/validate_live_event_source_integration.py",
    ]:
        path = ROOT / rel
        checks.append(check(f"metadata_consumer_present:{rel}", path.exists(), rel))
        if path.exists():
            text = path.read_text(encoding="utf-8")
            checks.append(check(f"no_release_name_allowlist:{rel}", "RELEASE_NAME in {" not in text, rel))
            checks.append(check(f"uses_release_name_presence:{rel}", "bool(RELEASE_NAME)" in text, rel))

    failed = [row for row in checks if not row[1]]
    print("Release Metadata Alignment Doctor")
    print("=" * 64)
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"\nOverall status: {'PASS' if not failed else 'FAIL'}")
    print(f"Passed: {len(checks) - len(failed)}")
    print(f"Failed: {len(failed)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
