"""Validation for v0.5.6.1.0c Capability Participation Audit."""
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

    from Core.capability_audit import (
        CAPABILITY_AUDIT_VERSION,
        audit_execution_trace,
        capability_audit_diagnostics,
        sample_capability_audit_report,
    )
    from Core.execution_trace import CapabilityTrace, create_execution_trace, sample_execution_trace
    from Core.capability_registry import seed_capability_registry

    checks.append(check("audit_version", CAPABILITY_AUDIT_VERSION == "0.5.6.1.0", CAPABILITY_AUDIT_VERSION))
    registry = seed_capability_registry()
    checks.append(check("registry_available", registry.summary().get("capability_count", 0) > 0, str(registry.summary().get("capability_count"))))

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
        evidence_expected=("team_profile",),
        evidence_found=("team_profile",),
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
        evidence_expected=("roster", "injuries", "recent_performance"),
        evidence_missing=("roster", "injuries", "recent_performance"),
    ))
    trace.complete(status="pass", confidence=0.61, final_response_summary="Validation audit sample")

    report = audit_execution_trace(trace, registry=registry)
    data = report.to_dict()
    checks.append(check("audit_report_created", report.trace_id == trace.trace_id, report.trace_id))
    checks.append(check("audit_expected_count", report.expected_count == 5, str(report.expected_count)))
    checks.append(check("audit_selected_count", report.selected_count == 2, str(report.selected_count)))
    checks.append(check("audit_skipped_count", report.skipped_count >= 1, str(report.skipped_count)))
    checks.append(check("audit_missing_count", report.missing_count >= 1, str(report.missing_count)))
    checks.append(check("audit_evidence_missing_count", report.evidence_missing_count == 4, str(report.evidence_missing_count)))
    checks.append(check("audit_records_classify_roster", any(r.capability_id == "roster_assessment" and r.skipped and "not selected" in r.reason for r in report.records), str([r.to_dict() for r in report.records])))
    checks.append(check("audit_records_classify_historical_missing", any(r.capability_id == "historical_assessment" and r.missing for r in report.records), str([r.to_dict() for r in report.records])))
    checks.append(check("audit_findings_actionable", any("expected" in f.lower() or "skipped" in f.lower() for f in report.findings), str(report.findings)))
    checks.append(check("audit_next_actions_actionable", any("routing" in a.lower() or "planner" in a.lower() or "evidence" in a.lower() for a in report.next_actions), str(report.next_actions)))
    checks.append(check("audit_json_serializable", isinstance(json.dumps(data), str), "json"))

    sample = sample_capability_audit_report()
    checks.append(check("sample_audit_has_gavin_prompt", "Gavin McKenna" in sample.prompt, sample.prompt))
    checks.append(check("sample_audit_has_missing_evidence", sample.evidence_missing_count > 0, str(sample.evidence_missing_count)))
    checks.append(check("sample_audit_has_records", len(sample.records) > 0, str(len(sample.records))))

    diag = capability_audit_diagnostics()
    checks.append(check("diagnostics_panel", diag.get("panel") == "capability_audit", str(diag.keys())))
    checks.append(check("diagnostics_supports_skipped_reasons", "skipped_capability_reasons" in diag.get("supports", []), str(diag.get("supports"))))

    failed = [c for c in checks if not c[1]]
    print("Capability Participation Audit Validation")
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
