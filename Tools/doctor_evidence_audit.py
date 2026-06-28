"""Doctor for v0.5.6.1.0d Evidence Audit Foundation."""
from __future__ import annotations

import json
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
        checks.append(check("version_at_least_0_5_6_1_0", tuple(map(int, ATHENA_VERSION.split('.'))) >= (0, 5, 6, 1, 0), ATHENA_VERSION))
        checks.append(check("athena_build", ATHENA_BUILD == ATHENA_VERSION, ATHENA_BUILD))
        checks.append(check("release_name_available", bool(RELEASE_NAME), RELEASE_NAME))
        checks.append(check("version_schema_locked", VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", VERSION_SCHEMA))
    except Exception as exc:
        checks.append(check("version_import", False, str(exc)))

    required = [
        "Core/execution_trace.py",
        "Core/capability_audit.py",
        "Core/evidence_audit.py",
        "Tools/doctor_evidence_audit.py",
        "Tests/validate_evidence_audit.py",
    ]
    for rel in required:
        checks.append(check(f"required_file:{rel}", (ROOT / rel).exists(), rel))

    try:
        from Core.evidence_audit import EVIDENCE_AUDIT_VERSION, evidence_audit_diagnostics, sample_evidence_audit_report
        checks.append(check("evidence_audit_version", EVIDENCE_AUDIT_VERSION == "0.5.6.1.0", EVIDENCE_AUDIT_VERSION))
        report = sample_evidence_audit_report()
        data = report.to_dict()
        checks.append(check("report_created", bool(data.get("trace_id")), data.get("trace_id", "")))
        checks.append(check("records_available", len(report.records) >= 3, str(len(report.records))))
        checks.append(check("required_missing_count_available", report.required_missing_count >= 1, str(report.required_missing_count)))
        checks.append(check("optional_missing_count_available", report.optional_missing_count >= 1, str(report.optional_missing_count)))
        checks.append(check("roster_gap_detected", any("roster" in r.missing_required or "roster" in r.missing_optional for r in report.records), "roster evidence gap"))
        checks.append(check("confidence_impact_available", any(r.confidence_impact > 0 for r in report.records), str([r.confidence_impact for r in report.records])))
        checks.append(check("findings_available", bool(report.findings), str(report.findings)))
        checks.append(check("next_actions_available", bool(report.next_actions), str(report.next_actions)))
        checks.append(check("json_serializable", isinstance(json.dumps(data), str), "json"))
        diag = evidence_audit_diagnostics()
        checks.append(check("studio_diagnostics_payload", diag.get("panel") == "evidence_audit", str(diag.get("supports"))))
        checks.append(check("diagnostics_supports_required_optional", "required_vs_optional_evidence" in diag.get("supports", []), str(diag.get("supports"))))
    except Exception as exc:
        checks.append(check("evidence_audit_import", False, f"{type(exc).__name__}: {exc}"))

    failed = [c for c in checks if not c[1]]
    print("Evidence Audit Doctor")
    print("=" * 64)
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"\nOverall status: {'PASS' if not failed else 'FAIL'}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
