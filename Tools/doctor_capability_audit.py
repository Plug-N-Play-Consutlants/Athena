"""Doctor for v0.5.6.1.0c Capability Participation Audit."""
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
        checks.append(check("version_at_least_0_5_6_1_0", tuple(map(int, ATHENA_VERSION.split('.'))) >= (0,5,6,1,0), ATHENA_VERSION))
        checks.append(check("athena_build", ATHENA_BUILD == ATHENA_VERSION, ATHENA_BUILD))
        checks.append(check("release_name_available", bool(RELEASE_NAME), RELEASE_NAME))
        checks.append(check("version_schema_locked", VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", VERSION_SCHEMA))
    except Exception as exc:
        checks.append(check("version_import", False, str(exc)))

    required = [
        "Core/capability_registry.py",
        "Core/execution_trace.py",
        "Core/capability_audit.py",
        "Tools/doctor_capability_audit.py",
        "Tests/validate_capability_audit.py",
    ]
    for rel in required:
        checks.append(check(f"required_file:{rel}", (ROOT / rel).exists(), rel))

    try:
        from Core.capability_audit import CAPABILITY_AUDIT_VERSION, capability_audit_diagnostics, sample_capability_audit_report
        checks.append(check("capability_audit_version", CAPABILITY_AUDIT_VERSION == "0.5.6.1.0", CAPABILITY_AUDIT_VERSION))
        report = sample_capability_audit_report()
        data = report.to_dict()
        checks.append(check("report_created", data.get("panel") is None and bool(data.get("trace_id")), data.get("trace_id", "")))
        checks.append(check("expected_count_available", report.expected_count >= 5, str(report.expected_count)))
        checks.append(check("selected_count_available", report.selected_count >= 1, str(report.selected_count)))
        checks.append(check("skipped_count_available", report.skipped_count >= 1, str(report.skipped_count)))
        checks.append(check("missing_count_available", report.missing_count >= 1, str(report.missing_count)))
        checks.append(check("records_include_player_assessment", any(r.capability_id == "player_assessment" for r in report.records), str([r.capability_id for r in report.records])))
        checks.append(check("records_include_roster_reason", any(r.capability_id == "roster_assessment" and r.reason for r in report.records), "roster_assessment"))
        checks.append(check("findings_available", bool(report.findings), str(report.findings)))
        checks.append(check("next_actions_available", bool(report.next_actions), str(report.next_actions)))
        checks.append(check("json_serializable", isinstance(json.dumps(data), str), "json"))
        diag = capability_audit_diagnostics()
        checks.append(check("studio_diagnostics_payload", diag.get("panel") == "capability_audit", str(diag.get("supports"))))
        checks.append(check("diagnostics_support_expected_vs_actual", "expected_vs_actual_capabilities" in diag.get("supports", []), str(diag.get("supports"))))
    except Exception as exc:
        checks.append(check("capability_audit_import", False, f"{type(exc).__name__}: {exc}"))

    failed = [c for c in checks if not c[1]]
    print("Capability Participation Audit Doctor")
    print("=" * 64)
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"\nOverall status: {'PASS' if not failed else 'FAIL'}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
