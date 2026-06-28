"""Validation for v0.5.6.1.0d Evidence Audit Foundation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check(name: str, condition: bool, detail: str = "") -> tuple[str, bool, str]:
    return (name, bool(condition), detail)


def version_at_least(value: str, minimum: tuple[int, int, int, int, int]) -> bool:
    try:
        return tuple(int(part) for part in value.split(".")) >= minimum
    except Exception:
        return False


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    from Core.version import ATHENA_VERSION, ATHENA_BUILD, RELEASE_NAME, VERSION_SCHEMA
    checks.append(check("athena_version", version_at_least(ATHENA_VERSION, (0, 5, 6, 1, 0)), ATHENA_VERSION))
    checks.append(check("athena_build", version_at_least(ATHENA_BUILD, (0, 5, 6, 1, 0)), ATHENA_BUILD))
    checks.append(check("release_name", bool(RELEASE_NAME), RELEASE_NAME))
    checks.append(check("version_schema", VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", VERSION_SCHEMA))

    from Core.execution_trace import CapabilityTrace, create_execution_trace, sample_execution_trace
    from Core.evidence_audit import (
        EVIDENCE_AUDIT_VERSION,
        audit_evidence,
        evidence_audit_diagnostics,
        sample_evidence_audit_report,
    )

    checks.append(check("audit_version", EVIDENCE_AUDIT_VERSION == "0.5.6.1.0", EVIDENCE_AUDIT_VERSION))

    trace = create_execution_trace("What are team weaknesses for the Canadiens?", mode="public", validator=True)
    trace.intent = "team_weakness_analysis"
    trace.entities = ("Montreal Canadiens",)
    trace.expected_capabilities = ("team_assessment", "roster_assessment", "historical_assessment", "reasoning", "response_composition")
    trace.selected_capabilities = ("team_assessment", "reasoning")
    trace.skipped_capabilities = ("roster_assessment", "response_composition")
    trace.evidence_requested = ("team_profile", "roster", "injuries", "recent_performance", "transactions")
    trace.evidence_found = ("team_profile",)
    trace.evidence_missing = ("roster", "injuries", "recent_performance", "transactions")
    trace.composition_inputs = ("team_assessment", "reasoning")
    trace.composition_outputs = ("summary", "limitations")
    trace.add_capability(CapabilityTrace(
        capability_id="team_assessment",
        expected=True,
        selected=True,
        executed=True,
        evidence_expected=("team_profile", "roster", "recent_performance"),
        evidence_found=("team_profile",),
        evidence_missing=("roster", "recent_performance"),
        output_keys=("identity", "strengths", "weaknesses"),
        included_output_keys=("identity",),
        discarded_output_keys=("weaknesses",),
        confidence=0.8,
    ))
    trace.add_capability(CapabilityTrace(
        capability_id="roster_assessment",
        expected=True,
        selected=False,
        executed=False,
        skipped=True,
        skip_reason="not selected by current planner/routing path",
        evidence_expected=("roster", "injuries", "lineup"),
        evidence_missing=("roster", "injuries", "lineup"),
    ))
    trace.complete(status="pass", confidence=0.61, final_response_summary="Validation evidence audit sample")

    report = audit_evidence(trace)
    data = report.to_dict()
    checks.append(check("evidence_report_created", report.trace_id == trace.trace_id, report.trace_id))
    checks.append(check("evidence_requested_count", report.evidence_requested_count == 5, str(report.evidence_requested_count)))
    checks.append(check("evidence_found_count", report.evidence_found_count == 1, str(report.evidence_found_count)))
    checks.append(check("evidence_missing_count", report.evidence_missing_count == 4, str(report.evidence_missing_count)))
    checks.append(check("required_missing_count", report.required_missing_count >= 4, str(report.required_missing_count)))
    checks.append(check("optional_missing_count", report.optional_missing_count >= 1, str(report.optional_missing_count)))
    checks.append(check("team_record_partial", any(r.capability_id == "team_assessment" and r.status == "partial" for r in report.records), str([r.to_dict() for r in report.records])))
    checks.append(check("roster_record_failed_or_partial", any(r.capability_id == "roster_assessment" and r.missing_required for r in report.records), str([r.to_dict() for r in report.records])))
    checks.append(check("coverage_ratio_bounded", all(0.0 <= r.coverage_ratio <= 1.0 for r in report.records), str([r.coverage_ratio for r in report.records])))
    checks.append(check("confidence_impact_bounded", all(0.0 <= r.confidence_impact <= 0.75 for r in report.records), str([r.confidence_impact for r in report.records])))
    checks.append(check("findings_actionable", any("missing" in f.lower() or "evidence" in f.lower() for f in report.findings), str(report.findings)))
    checks.append(check("next_actions_actionable", any("evidence" in a.lower() or "roster" in a.lower() for a in report.next_actions), str(report.next_actions)))
    checks.append(check("json_serializable", isinstance(json.dumps(data), str), "json"))

    sample = sample_evidence_audit_report()
    checks.append(check("sample_uses_gavin_prompt", "Gavin McKenna" in sample.prompt, sample.prompt))
    checks.append(check("sample_has_records", len(sample.records) > 0, str(len(sample.records))))
    checks.append(check("sample_has_missing_evidence", sample.evidence_missing_count > 0 or sample.required_missing_count > 0, f"trace={sample.evidence_missing_count}; required={sample.required_missing_count}"))

    diag = evidence_audit_diagnostics()
    checks.append(check("diagnostics_panel", diag.get("panel") == "evidence_audit", str(diag.keys())))
    checks.append(check("diagnostics_supports_confidence_impact", "confidence_impact_estimates" in diag.get("supports", []), str(diag.get("supports"))))

    failed = [c for c in checks if not c[1]]
    print("Evidence Audit Validation")
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
