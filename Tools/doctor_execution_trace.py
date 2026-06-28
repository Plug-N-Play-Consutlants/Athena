"""Doctor for v0.5.6.1.0 Execution Trace Foundation."""
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
        "Core/execution_trace.py",
        "Tools/doctor_execution_trace.py",
        "Tests/validate_execution_trace.py",
    ]
    for rel in required:
        checks.append(check(f"required_file:{rel}", (ROOT / rel).exists(), rel))

    try:
        from Core.execution_trace import (
            EXECUTION_TRACE_VERSION,
            CapabilityTrace,
            ExecutionStage,
            ExecutionTrace,
            create_execution_trace,
            execution_trace_diagnostics,
            persist_execution_trace,
            sample_execution_trace,
        )
        checks.append(check("execution_trace_version", EXECUTION_TRACE_VERSION == "0.5.6.1.0", EXECUTION_TRACE_VERSION))
        trace = sample_execution_trace()
        data = trace.to_dict()
        summary = trace.audit_summary()
        checks.append(check("sample_trace_created", bool(trace.trace_id), trace.trace_id))
        checks.append(check("sample_trace_has_stages", len(trace.stages) >= 5, str(len(trace.stages))))
        checks.append(check("sample_trace_has_capability_participation", len(trace.capabilities) >= 2, str(len(trace.capabilities))))
        checks.append(check("expected_vs_selected_available", bool(summary.get("missing_expected_capabilities")), str(summary.get("missing_expected_capabilities"))))
        checks.append(check("evidence_audit_available", bool(trace.evidence_missing), ",".join(trace.evidence_missing)))
        checks.append(check("composition_audit_counts_available", summary.get("composition_inputs", 0) > 0 and summary.get("composition_outputs", 0) > 0, str(summary)))
        checks.append(check("trace_serializable", isinstance(json.dumps(data), str), "json"))
        temp_dir = ROOT / "Reports" / "execution_trace_doctor_tmp"
        path = persist_execution_trace(trace, folder=temp_dir)
        checks.append(check("trace_persistence", path.exists(), str(path.relative_to(ROOT))))
        diag = execution_trace_diagnostics()
        checks.append(check("studio_diagnostics_payload", diag.get("panel") == "execution_trace", str(diag.get("summary", {}).get("status"))))
    except Exception as exc:
        checks.append(check("execution_trace_import", False, f"{type(exc).__name__}: {exc}"))

    failed = [c for c in checks if not c[1]]
    print("Execution Trace Doctor")
    print("=" * 64)
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"\nOverall status: {'PASS' if not failed else 'FAIL'}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
