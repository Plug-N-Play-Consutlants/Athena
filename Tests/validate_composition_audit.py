"""Validation for v0.5.6.1.0e Composition Audit Foundation."""
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
    from Core.version import ATHENA_VERSION, ATHENA_BUILD, RELEASE_NAME, VERSION_SCHEMA
    checks.append(check("athena_version", tuple(map(int, ATHENA_VERSION.split('.'))) >= (0, 5, 6, 1, 0), ATHENA_VERSION))
    checks.append(check("athena_build", tuple(map(int, ATHENA_BUILD.split('.'))) >= (0, 5, 6, 1, 0), ATHENA_BUILD))
    checks.append(check("release_name", bool(RELEASE_NAME), RELEASE_NAME))
    checks.append(check("version_schema", VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", VERSION_SCHEMA))

    from Core.execution_trace import CapabilityTrace, create_execution_trace
    from Core.composition_audit import (
        COMPOSITION_AUDIT_VERSION,
        audit_composition,
        composition_audit_diagnostics,
        sample_composition_audit_report,
    )

    checks.append(check("audit_version", COMPOSITION_AUDIT_VERSION == "0.5.6.1.0", COMPOSITION_AUDIT_VERSION))

    trace = create_execution_trace("What are team weaknesses for the Canadiens?", mode="public", validator=True)
    trace.intent = "team_weakness_analysis"
    trace.entities = ("Montreal Canadiens",)
    trace.expected_capabilities = ("team_assessment", "roster_assessment", "historical_assessment", "reasoning", "response_composition")
    trace.selected_capabilities = ("team_assessment", "reasoning")
    trace.skipped_capabilities = ("roster_assessment", "response_composition")
    trace.composition_inputs = ("team_assessment", "reasoning")
    trace.composition_outputs = ("executive_summary", "limitations")
    trace.add_capability(CapabilityTrace(
        capability_id="team_assessment",
        expected=True,
        selected=True,
        executed=True,
        output_keys=("team_profile", "strengths", "weaknesses", "roster_construction"),
        included_output_keys=("team_profile",),
        discarded_output_keys=("weaknesses", "roster_construction"),
        confidence=0.8,
    ))
    trace.add_capability(CapabilityTrace(
        capability_id="historical_assessment",
        expected=True,
        selected=True,
        executed=True,
        output_keys=("historical_trends",),
        discarded_output_keys=("historical_trends",),
        confidence=0.7,
    ))
    trace.add_capability(CapabilityTrace(
        capability_id="reasoning",
        expected=True,
        selected=True,
        executed=True,
        output_keys=("executive_summary", "limitations"),
        included_output_keys=("executive_summary", "limitations"),
        confidence=0.62,
    ))
    trace.complete(status="pass", confidence=0.62, final_response_summary="Validation composition audit sample")

    report = audit_composition(trace)
    data = report.to_dict()
    checks.append(check("composition_report_created", report.trace_id == trace.trace_id, report.trace_id))
    checks.append(check("generated_count", report.generated_count >= 5, str(report.generated_count)))
    checks.append(check("displayed_count", report.displayed_count == 2, str(report.displayed_count)))
    checks.append(check("included_count", report.included_count >= 2, str(report.included_count)))
    checks.append(check("discarded_count", report.discarded_count >= 3, str(report.discarded_count)))
    checks.append(check("coverage_ratio_bounded", 0.0 <= report.coverage_ratio <= 1.0, str(report.coverage_ratio)))
    checks.append(check("team_record_partial", any(r.capability_id == "team_assessment" and r.status == "partial" for r in report.records), str([r.to_dict() for r in report.records])))
    checks.append(check("weaknesses_discarded", any("weaknesses" in r.discarded_sections for r in report.records), str([r.to_dict() for r in report.records])))
    checks.append(check("historical_discarded", any("historical_trends" in r.discarded_sections for r in report.records), str([r.to_dict() for r in report.records])))
    checks.append(check("discard_reasons_available", any(r.discard_reasons for r in report.records), str([r.to_dict() for r in report.records])))
    checks.append(check("findings_actionable", any("section" in f.lower() or "composition" in f.lower() for f in report.findings), str(report.findings)))
    checks.append(check("next_actions_actionable", any("template" in a.lower() or "composition" in a.lower() or "section" in a.lower() for a in report.next_actions), str(report.next_actions)))
    checks.append(check("json_serializable", isinstance(json.dumps(data), str), "json"))

    sample = sample_composition_audit_report()
    checks.append(check("sample_uses_gavin_prompt", "Gavin McKenna" in sample.prompt, sample.prompt))
    checks.append(check("sample_has_records", len(sample.records) > 0, str(len(sample.records))))
    checks.append(check("sample_has_discarded_output", sample.discarded_count > 0, str(sample.discarded_count)))

    diag = composition_audit_diagnostics()
    checks.append(check("diagnostics_panel", diag.get("panel") == "composition_audit", str(diag.keys())))
    checks.append(check("diagnostics_supports_coverage", "composition_coverage_ratio" in diag.get("supports", []), str(diag.get("supports"))))

    failed = [c for c in checks if not c[1]]
    print("Composition Audit Validation")
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
