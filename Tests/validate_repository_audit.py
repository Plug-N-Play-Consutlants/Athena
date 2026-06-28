"""Validate the AthenaEngine Repository Audit Foundation."""
from __future__ import annotations

import json
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REQUIRED_SECTION_KEYS = {
    "root_markers",
    "duplicate_repository_structures",
    "duplicate_module_basenames",
    "shim_modules",
    "root_document_inventory",
    "runtime_artifacts",
    "empty_directories",
    "dependency_graph_summary",
    "packaging_ci_readiness",
    "version_metadata",
    "version_1_release_readiness",
}


def fail(message: str) -> int:
    print("Overall status: FAIL")
    print(f"[FAIL] {message}")
    return 1


def main() -> int:
    print("Repository Audit Foundation Validation")
    print("=" * 64)
    failures: list[str] = []
    for rel in ["Tools/repository_audit.py", "Tools/doctor_repository_audit.py", "Tests/validate_repository_audit.py"]:
        path = ROOT / rel
        if not path.exists():
            failures.append(f"missing required file: {rel}")
        else:
            print(f"[PASS] required file: {rel}")
            try:
                py_compile.compile(str(path), doraise=True)
                print(f"[PASS] py_compile: {rel}")
            except Exception as exc:
                failures.append(f"py_compile failed for {rel}: {exc}")

    from Core.version import ATHENA_BUILD, ATHENA_VERSION, RELEASE_NAME, VERSION_SCHEMA
    if ATHENA_VERSION != ATHENA_BUILD or ATHENA_VERSION < "0.5.6.2.0":
        failures.append(f"version metadata not advanced/aligned: {ATHENA_VERSION} / {ATHENA_BUILD}")
    else:
        print(f"[PASS] version metadata: {ATHENA_VERSION} / {ATHENA_BUILD}")
    if VERSION_SCHEMA != "major.epic.sprint.patch.hotfix":
        failures.append(f"unexpected version schema: {VERSION_SCHEMA}")
    else:
        print(f"[PASS] version schema: {VERSION_SCHEMA}")
    if not RELEASE_NAME:
        failures.append("release name missing")
    else:
        print(f"[PASS] release name: {RELEASE_NAME}")

    from Tools.repository_audit import AUDIT_VERSION, audit_repository, write_repository_audit_report
    if AUDIT_VERSION != "0.5.6.2.0":
        failures.append(f"unexpected audit version: {AUDIT_VERSION}")
    else:
        print(f"[PASS] audit version: {AUDIT_VERSION}")

    audit = audit_repository(ROOT)
    if audit.status not in {"pass", "warn", "fail"}:
        failures.append(f"invalid audit status: {audit.status}")
    else:
        print(f"[PASS] audit status bounded: {audit.status}")
    missing_sections = sorted(REQUIRED_SECTION_KEYS - set(audit.sections.keys()))
    if missing_sections:
        failures.append("missing audit sections: " + ", ".join(missing_sections))
    else:
        print(f"[PASS] audit sections complete: {len(REQUIRED_SECTION_KEYS)}")

    summary = audit.sections.get("dependency_graph_summary", {})
    if not isinstance(summary, dict) or int(summary.get("python_files", 0)) <= 0:
        failures.append("dependency graph summary did not count Python files")
    else:
        print(f"[PASS] dependency graph summary: {summary}")

    readiness = audit.sections.get("version_1_release_readiness", {})
    if not isinstance(readiness, dict) or "ready_for_release_candidate" not in readiness:
        failures.append("release readiness summary missing")
    else:
        print(f"[PASS] release readiness summary: {readiness}")

    packaging = audit.sections.get("packaging_ci_readiness", {})
    if not isinstance(packaging, dict) or ".github/workflows" not in packaging:
        failures.append("packaging/CI readiness section incomplete")
    else:
        print(f"[PASS] packaging/CI readiness: {packaging}")

    report_path = write_repository_audit_report(ROOT)
    if not report_path.exists():
        failures.append("repository audit report was not written")
    else:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        if payload.get("version") != "0.5.6.2.0" or "sections" not in payload or "findings" not in payload:
            failures.append("repository audit report payload incomplete")
        else:
            print(f"[PASS] repository audit report written: {report_path}")

    print("-" * 64)
    if failures:
        print("Overall status: FAIL")
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1
    print("Overall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
