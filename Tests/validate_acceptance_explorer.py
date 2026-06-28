"""Validation for v0.5.6.1.0f Acceptance Explorer Foundation."""
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
    from Core.acceptance_explorer import (
        ACCEPTANCE_EXPLORER_VERSION,
        acceptance_explorer_diagnostics,
        build_acceptance_report,
        sample_acceptance_report,
        sample_acceptance_trace,
    )

    checks.append(check("acceptance_version", ACCEPTANCE_EXPLORER_VERSION == "0.5.6.1.0", ACCEPTANCE_EXPLORER_VERSION))

    trace = create_execution_trace("What are team weaknesses for the Canadiens?", mode="public", validator=True)
    trace.intent = "team_weakness_analysis"
    trace.entities = ("Montreal Canadiens",)
    trace.expected_capabilities = ("team_assessment", "roster_assessment", "historical_assessment", "reasoning", "response_composition")
    trace.selected_capabilities = ("team_assessment", "reasoning")
    trace.skipped_capabilities = ("roster_assessment", "response_composition")
    trace.evidence_requested = ("team_profile", "roster", "recent_form", "transactions", "salary_cap")
    trace.evidence_found = ("team_profile", "transactions")
    trace.evidence_missing = ("roster", "recent_form", "salary_cap")
    trace.composition_inputs = ("team_assessment", "reasoning")
    trace.composition_outputs = ("executive_summary", "limitations")
    trace.add_capability(CapabilityTrace(
        capability_id="team_assessment",
        expected=True,
        selected=True,
        executed=True,
        evidence_expected=("team_profile", "roster", "recent_form", "transactions"),
        evidence_found=("team_profile", "transactions"),
        evidence_missing=("roster", "recent_form"),
        output_keys=("team_profile", "strengths", "weaknesses", "roster_construction"),
        included_output_keys=("team_profile",),
        discarded_output_keys=("weaknesses", "roster_construction"),
        confidence=0.8,
    ))
    trace.add_capability(CapabilityTrace(
        capability_id="reasoning",
        expected=True,
        selected=True,
        executed=True,
        evidence_expected=("team_profile", "roster", "recent_form"),
        evidence_found=("team_profile",),
        evidence_missing=("roster", "recent_form"),
        output_keys=("executive_summary", "limitations"),
        included_output_keys=("executive_summary", "limitations"),
        confidence=0.68,
    ))
    trace.complete(status="pass", confidence=0.68, final_response_summary="Validation acceptance explorer sample")

    report = build_acceptance_report(trace)
    data = report.to_dict()
    checks.append(check("report_created", report.trace_id == trace.trace_id, report.trace_id))
    checks.append(check("prompt_preserved", "Canadiens" in report.prompt, report.prompt))
    checks.append(check("intent_preserved", report.intent == "team_weakness_analysis", report.intent))
    checks.append(check("entities_preserved", "Montreal Canadiens" in report.entities, str(report.entities)))
    checks.append(check("sections_present", {"execution", "capabilities", "evidence", "composition"}.issubset({s.section_id for s in report.sections}), str([s.section_id for s in report.sections])))
    checks.append(check("missing_capabilities_reported", "historical_assessment" in report.missing_expected_capabilities, str(report.missing_expected_capabilities)))
    checks.append(check("skipped_capabilities_reported", "roster_assessment" in report.skipped_capabilities, str(report.skipped_capabilities)))
    checks.append(check("evidence_counts", report.evidence_missing_count >= 3 and report.evidence_found_count >= 2, f"found={report.evidence_found_count}; missing={report.evidence_missing_count}"))
    checks.append(check("required_evidence_gaps", report.required_evidence_missing_count >= 1, str(report.required_evidence_missing_count)))
    checks.append(check("composition_discarded", report.discarded_section_count >= 2, str(report.discarded_section_count)))
    checks.append(check("coverage_ratio_bounded", 0.0 <= report.composition_coverage_ratio <= 1.0, str(report.composition_coverage_ratio)))
    checks.append(check("capability_audit_included", bool(report.capability_audit.get("records")), "capability audit"))
    checks.append(check("evidence_audit_included", bool(report.evidence_audit.get("records")), "evidence audit"))
    checks.append(check("composition_audit_included", bool(report.composition_audit.get("records")), "composition audit"))
    checks.append(check("findings_actionable", any("capabil" in f.lower() or "evidence" in f.lower() or "section" in f.lower() for f in report.findings), str(report.findings)))
    checks.append(check("next_actions_actionable", any("routing" in a.lower() or "evidence" in a.lower() or "composition" in a.lower() or "template" in a.lower() for a in report.next_actions), str(report.next_actions)))
    checks.append(check("json_serializable", isinstance(json.dumps(data), str), "json"))

    sample_trace = sample_acceptance_trace()
    checks.append(check("sample_trace_uses_gavin_prompt", "Gavin McKenna" in sample_trace.prompt, sample_trace.prompt))
    sample = sample_acceptance_report()
    checks.append(check("sample_report_has_sections", len(sample.sections) >= 4, str(len(sample.sections))))
    checks.append(check("sample_report_warns_on_gaps", sample.status == "warn", sample.status))
    checks.append(check("sample_report_has_next_actions", bool(sample.next_actions), str(sample.next_actions)))

    diag = acceptance_explorer_diagnostics()
    checks.append(check("diagnostics_panel", diag.get("panel") == "acceptance_explorer", str(diag.keys())))
    checks.append(check("diagnostics_supports_prompt_level", "prompt_level_diagnostics" in diag.get("supports", []), str(diag.get("supports"))))

    failed = [c for c in checks if not c[1]]
    print("Acceptance Explorer Validation")
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
