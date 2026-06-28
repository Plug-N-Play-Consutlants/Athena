"""Doctor for v0.5.6.1.0f Acceptance Explorer Foundation."""
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
        "Core/acceptance_explorer.py",
        "Core/execution_trace.py",
        "Core/capability_audit.py",
        "Core/evidence_audit.py",
        "Core/composition_audit.py",
        "Tools/doctor_acceptance_explorer.py",
        "Tests/validate_acceptance_explorer.py",
    ]
    for rel in required:
        checks.append(check(f"required_file:{rel}", (ROOT / rel).exists(), rel))

    try:
        from Core.acceptance_explorer import (
            ACCEPTANCE_EXPLORER_VERSION,
            acceptance_explorer_diagnostics,
            sample_acceptance_report,
            sample_acceptance_trace,
        )
        checks.append(check("acceptance_explorer_version", ACCEPTANCE_EXPLORER_VERSION == "0.5.6.1.0", ACCEPTANCE_EXPLORER_VERSION))
        trace = sample_acceptance_trace()
        checks.append(check("sample_trace_created", bool(trace.trace_id), trace.trace_id))
        checks.append(check("sample_trace_targets_impact", trace.intent == "organizational_impact", trace.intent))
        checks.append(check("sample_trace_has_expected_capabilities", len(trace.expected_capabilities) >= 5, str(trace.expected_capabilities)))
        report = sample_acceptance_report()
        data = report.to_dict()
        checks.append(check("report_created", bool(data.get("trace_id")), data.get("trace_id", "")))
        checks.append(check("report_status_present", report.status in {"pass", "warn", "fail"}, report.status))
        checks.append(check("sections_available", len(report.sections) >= 4, str([s.section_id for s in report.sections])))
        checks.append(check("capability_audit_attached", bool(report.capability_audit.get("records")), "capability records"))
        checks.append(check("evidence_audit_attached", bool(report.evidence_audit.get("records")), "evidence records"))
        checks.append(check("composition_audit_attached", bool(report.composition_audit.get("records")), "composition records"))
        checks.append(check("missing_capabilities_detected", len(report.missing_expected_capabilities) >= 1, str(report.missing_expected_capabilities)))
        checks.append(check("evidence_gaps_detected", report.evidence_missing_count >= 1, str(report.evidence_missing_count)))
        checks.append(check("composition_gaps_detected", report.discarded_section_count >= 1, str(report.discarded_section_count)))
        checks.append(check("findings_available", bool(report.findings), str(report.findings)))
        checks.append(check("next_actions_available", bool(report.next_actions), str(report.next_actions)))
        checks.append(check("json_serializable", isinstance(json.dumps(data), str), "json"))
        diag = acceptance_explorer_diagnostics()
        checks.append(check("studio_diagnostics_payload", diag.get("panel") == "acceptance_explorer", str(diag.get("supports"))))
        checks.append(check("diagnostics_supports_single_pane", "single_pane_acceptance_review" in diag.get("supports", []), str(diag.get("supports"))))
    except Exception as exc:
        checks.append(check("acceptance_explorer_import", False, f"{type(exc).__name__}: {exc}"))

    failed = [c for c in checks if not c[1]]
    print("Acceptance Explorer Doctor")
    print("=" * 64)
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"\nOverall status: {'PASS' if not failed else 'FAIL'}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
