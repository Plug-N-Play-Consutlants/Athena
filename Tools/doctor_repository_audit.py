"""Doctor for the AthenaEngine Repository Audit Foundation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REQUIRED_FILES = [
    "Tools/repository_audit.py",
    "Tools/doctor_repository_audit.py",
    "Tests/validate_repository_audit.py",
]


def report(name: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))
    return ok


def main() -> int:
    print("Repository Audit Foundation Doctor")
    print("=" * 64)
    checks: list[bool] = []
    for rel in REQUIRED_FILES:
        checks.append(report(f"required file exists: {rel}", (PROJECT_ROOT / rel).exists(), rel))

    from Core.version import ATHENA_BUILD, ATHENA_VERSION, RELEASE_NAME, VERSION_SCHEMA
    from Tools.repository_audit import AUDIT_VERSION, audit_repository, write_repository_audit_report

    checks.append(report("version schema locked", VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", VERSION_SCHEMA))
    checks.append(report("version metadata matches", ATHENA_VERSION == ATHENA_BUILD and ATHENA_VERSION >= "0.5.6.2.0", f"{ATHENA_VERSION} / {ATHENA_BUILD}"))
    checks.append(report("release name available", bool(RELEASE_NAME), RELEASE_NAME))
    checks.append(report("audit version", AUDIT_VERSION == "0.5.6.2.0", AUDIT_VERSION))

    audit = audit_repository(PROJECT_ROOT)
    checks.append(report("audit status bounded", audit.status in {"pass", "warn", "fail"}, audit.status))
    checks.append(report("audit sections present", len(audit.sections) >= 8, ", ".join(sorted(audit.sections.keys())[:8])))
    required_sections = {
        "root_markers",
        "duplicate_repository_structures",
        "duplicate_module_basenames",
        "shim_modules",
        "runtime_artifacts",
        "dependency_graph_summary",
        "packaging_ci_readiness",
        "version_1_release_readiness",
    }
    checks.append(report("audit covers required Phase 3 areas", required_sections.issubset(audit.sections.keys()), ", ".join(sorted(required_sections - set(audit.sections.keys())))))
    checks.append(report("audit is read-only", "cleanup" not in [f.area for f in audit.findings if f.severity == "fail"], "no cleanup actions executed"))

    path = write_repository_audit_report(PROJECT_ROOT)
    checks.append(report("audit report written", path.exists(), str(path)))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        checks.append(report("audit report json", payload.get("version") == "0.5.6.2.0" and "findings" in payload, payload.get("status", "")))
    except Exception as exc:
        checks.append(report("audit report json", False, str(exc)))

    print("-" * 64)
    failed = len([ok for ok in checks if not ok])
    print(f"Passed: {len(checks)-failed}")
    print(f"Failed: {failed}")
    print("Overall status:", "PASS" if failed == 0 else "FAIL")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
