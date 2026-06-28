"""Doctor for v0.5.6.1.0e Composition Audit Foundation."""
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
        "Core/composition_audit.py",
        "Tools/doctor_composition_audit.py",
        "Tests/validate_composition_audit.py",
    ]
    for rel in required:
        checks.append(check(f"required_file:{rel}", (ROOT / rel).exists(), rel))

    try:
        from Core.composition_audit import COMPOSITION_AUDIT_VERSION, composition_audit_diagnostics, sample_composition_audit_report
        checks.append(check("composition_audit_version", COMPOSITION_AUDIT_VERSION == "0.5.6.1.0", COMPOSITION_AUDIT_VERSION))
        report = sample_composition_audit_report()
        data = report.to_dict()
        checks.append(check("report_created", bool(data.get("trace_id")), data.get("trace_id", "")))
        checks.append(check("records_available", len(report.records) >= 3, str(len(report.records))))
        checks.append(check("generated_count_available", report.generated_count >= 4, str(report.generated_count)))
        checks.append(check("discarded_count_available", report.discarded_count >= 2, str(report.discarded_count)))
        checks.append(check("coverage_ratio_bounded", 0.0 <= report.coverage_ratio <= 1.0, str(report.coverage_ratio)))
        checks.append(check("weaknesses_discard_detected", any("weaknesses" in r.discarded_sections for r in report.records), "weaknesses discarded"))
        checks.append(check("roster_or_draft_gap_detected", any(set(r.discarded_sections) & {"roster_construction", "draft_impact"} for r in report.records), "roster/draft discarded"))
        checks.append(check("findings_available", bool(report.findings), str(report.findings)))
        checks.append(check("next_actions_available", bool(report.next_actions), str(report.next_actions)))
        checks.append(check("json_serializable", isinstance(json.dumps(data), str), "json"))
        diag = composition_audit_diagnostics()
        checks.append(check("studio_diagnostics_payload", diag.get("panel") == "composition_audit", str(diag.get("supports"))))
        checks.append(check("diagnostics_supports_discarded_output", "discarded_output_tracking" in diag.get("supports", []), str(diag.get("supports"))))
    except Exception as exc:
        checks.append(check("composition_audit_import", False, f"{type(exc).__name__}: {exc}"))

    failed = [c for c in checks if not c[1]]
    print("Composition Audit Doctor")
    print("=" * 64)
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"\nOverall status: {'PASS' if not failed else 'FAIL'}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
