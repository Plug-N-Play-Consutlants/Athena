"""Validation for v0.5.6.1.0 Execution Trace Foundation."""
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

    from Core.execution_trace import (
        EXECUTION_TRACE_VERSION,
        CapabilityTrace,
        ExecutionTrace,
        create_execution_trace,
        execution_trace_diagnostics,
        load_execution_trace,
        persist_execution_trace,
        sample_execution_trace,
    )

    checks.append(check("trace_version", EXECUTION_TRACE_VERSION == "0.5.6.1.0", EXECUTION_TRACE_VERSION))
    trace = create_execution_trace("Matthews vs McDavid", mode="public", validator=True)
    trace.intent = "comparison"
    trace.entities = ("Auston Matthews", "Connor McDavid")
    trace.expected_capabilities = ("player_assessment", "historical_assessment", "comparison_reasoning", "response_composition")
    trace.selected_capabilities = ("player_assessment", "comparison_reasoning")
    trace.skipped_capabilities = ("historical_assessment", "response_composition")
    trace.evidence_requested = ("player_profiles", "history", "style", "production")
    trace.evidence_found = ("player_profiles", "style")
    trace.evidence_missing = ("history", "production")
    stage = trace.add_stage("intent_classification", "Intent Classification", {"prompt": trace.prompt})
    stage.complete(detail="comparison", outputs={"intent": trace.intent}, confidence=0.9)
    trace.add_stage("capability_selection", "Capability Selection", {"intent": trace.intent}).complete(
        detail="partial comparison route", outputs={"selected": list(trace.selected_capabilities)}, confidence=0.7
    )
    trace.add_capability(CapabilityTrace(
        capability_id="historical_assessment",
        expected=True,
        selected=False,
        skipped=True,
        skip_reason="not selected in validation sample",
        evidence_expected=("history",),
        evidence_missing=("history",),
    ))
    trace.complete(status="pass", confidence=0.73, final_response_summary="Validation sample trace")

    data = trace.to_dict()
    summary = trace.audit_summary()
    checks.append(check("trace_created", data["trace_id"].startswith("trace_"), data["trace_id"]))
    checks.append(check("trace_has_stage_timing", data["stages"][0]["duration_ms"] >= 0, str(data["stages"][0].get("duration_ms"))))
    checks.append(check("trace_has_intent", data["intent"] == "comparison", data["intent"]))
    checks.append(check("trace_has_entities", len(data["entities"]) == 2, str(data["entities"])))
    checks.append(check("trace_expected_capabilities", len(data["expected_capabilities"]) == 4, str(data["expected_capabilities"])))
    checks.append(check("trace_missing_expected_capabilities", "historical_assessment" not in summary.get("missing_expected_capabilities", []), str(summary)))
    checks.append(check("trace_evidence_missing", set(data["evidence_missing"]) == {"history", "production"}, str(data["evidence_missing"])))
    checks.append(check("trace_capability_participation", data["capabilities"][0]["capability_id"] == "historical_assessment", str(data["capabilities"])))
    checks.append(check("trace_json_serializable", isinstance(json.dumps(data), str), "json"))

    sample = sample_execution_trace()
    sample_summary = sample.audit_summary()
    checks.append(check("sample_trace_models_gavin_prompt", "Gavin McKenna" in sample.prompt, sample.prompt))
    checks.append(check("sample_trace_surfaces_missing_evidence", "cap" in sample.evidence_missing, str(sample.evidence_missing)))
    checks.append(check("sample_trace_surfaces_missing_capabilities", "historical_assessment" in sample_summary.get("missing_expected_capabilities", []), str(sample_summary)))
    out_dir = ROOT / "Reports" / "execution_trace_validation_tmp"
    path = persist_execution_trace(sample, folder=out_dir)
    loaded = load_execution_trace(path)
    checks.append(check("trace_persist_and_load", loaded.get("trace_id") == sample.trace_id, str(path.relative_to(ROOT))))

    diag = execution_trace_diagnostics()
    checks.append(check("diagnostics_serializable", isinstance(diag, dict) and diag.get("panel") == "execution_trace", str(diag.keys())))
    checks.append(check("diagnostics_supports_expected", "expected_vs_selected_capabilities" in diag.get("supports", []), str(diag.get("supports"))))

    failed = [c for c in checks if not c[1]]
    print("Execution Trace Validation")
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
