"""Validation for Evidence Path Audit v0.5.5.5.19."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def report(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")
    return passed


def main() -> int:
    print("Evidence Path Audit Validation")
    print("=" * 64)
    checks: list[bool] = []

    from Core.version import ATHENA_VERSION, SCOUT_VERSION, RELEASE_NAME
    checks.append(report("athena_version", ATHENA_VERSION == "0.5.5.5.19", ATHENA_VERSION))
    checks.append(report("scout_version", SCOUT_VERSION == "v0.5.5.5.19", SCOUT_VERSION))
    checks.append(report("release_name", "Evidence Path Audit" in RELEASE_NAME, RELEASE_NAME))

    audit = ROOT / "docs" / "EVIDENCE_PATH_AUDIT_v0.5.5.5.19.md"
    structure = ROOT / "docs" / "PROGRAM_STRUCTURE_DIRECTION_v0.5.5.5.19.md"
    checks.append(report("audit_doc_exists", audit.exists(), str(audit)))
    checks.append(report("structure_doc_exists", structure.exists(), str(structure)))
    text = audit.read_text(encoding="utf-8") if audit.exists() else ""

    required_phrases = [
        "Specific entity + specific analytical intent must beat broad fallback.",
        "Evidence Request Contract for team_weakness",
        "Event Answer Contract",
        "Draft Evidence Contract",
        "Runtime orchestration is diagnostic, not canonical.",
        "A future acceptance patch should not be considered complete unless it answers these questions",
    ]
    for phrase in required_phrases:
        checks.append(report(f"audit_phrase:{phrase[:40]}", phrase in text))

    # Confirm the current Scout route map document remains present so the new audit extends it rather than replacing it.
    route_map = ROOT / "docs" / "SCOUT_ROUTE_MAP_v0.5.5.5.18.md"
    checks.append(report("prior_route_map_retained", route_map.exists(), str(route_map)))

    # Root package version should not drift behind Core.version again.
    root_init = (ROOT / "__init__.py").read_text(encoding="utf-8")
    checks.append(report("root_version_imports_core_version", "from Core.version import ATHENA_VERSION" in root_init))
    checks.append(report("root_version_uses_core_version", "__version__ = ATHENA_VERSION" in root_init))

    passed = sum(1 for item in checks if item)
    failed = len(checks) - passed
    print("-" * 64)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("Overall status:", "PASS" if failed == 0 else "FAIL")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
