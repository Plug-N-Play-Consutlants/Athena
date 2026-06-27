"""Doctor for v0.5.5.5.0 Runtime Orchestration & Observability."""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("ATHENA_SCOUT_LIVE_NETWORK", "0")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check(name: str, condition: bool, detail: str = "") -> tuple[str, bool, str]:
    return (name, bool(condition), detail)


def main() -> int:
    checks = []
    try:
        from Core.version import ATHENA_VERSION, VERSION_SCHEMA, RELEASE_NAME
        checks.append(check("version_at_least_0_5_5_5", tuple(map(int, ATHENA_VERSION.split('.'))) >= (0,5,5,5,0), ATHENA_VERSION))
        checks.append(check("version_schema_locked", VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", VERSION_SCHEMA))
        checks.append(check("release_name", RELEASE_NAME in {"Runtime Orchestration & Observability", "Scout Runtime Acceptance Hotfix", "Studio Log Visibility Hotfix", "Scout Runtime Continuation Hotfix", "Scout Session Logging Hotfix", "Scout Acceptance Communication Hotfix", "Public Analytical Routing Hotfix", "Response Composition Visibility Hotfix", "Acceptance Repository Cleanup and Pathway Audit", "Diagnostics Log Export Restoration"} or "Runtime Orchestration" in RELEASE_NAME, RELEASE_NAME))
    except Exception as exc:
        checks.append(check("version_import", False, str(exc)))
    required = [
        "Intelligence/Runtime/__init__.py",
        "Intelligence/Runtime/models.py",
        "Intelligence/Runtime/orchestrator.py",
        "Tests/validate_runtime_orchestration_observability.py",
    ]
    for rel in required:
        checks.append(check(f"required_file:{rel}", (ROOT/rel).exists(), rel))
    try:
        from Intelligence.Runtime import RUNTIME_ORCHESTRATION_VERSION, run_runtime_trace, studio_runtime_observability_diagnostics
        checks.append(check("runtime_version", RUNTIME_ORCHESTRATION_VERSION.startswith("0.5.5.5"), RUNTIME_ORCHESTRATION_VERSION))
        trace = run_runtime_trace("Who is Auston Matthews?")
        checks.append(check("trace_created", trace is not None, trace.status))
        checks.append(check("trace_has_five_stages", len(trace.stages) >= 5, str(len(trace.stages))))
        checks.append(check("trace_stage_names", {"routing","live_intelligence","explainability_pipeline","cross_sport_reasoning","response_assembly"}.issubset({s.name for s in trace.stages}), ",".join(s.name for s in trace.stages)))
        checks.append(check("trace_no_failed_stages", not trace.failed_stages, str([s.name for s in trace.failed_stages])))
        checks.append(check("evidence_ledger_available", len(trace.evidence_ledger) >= 1, str(len(trace.evidence_ledger))))
        diag = studio_runtime_observability_diagnostics()
        checks.append(check("studio_diagnostics", diag.get("panel") == "runtime_orchestration_observability", str(diag.get("status"))))
    except Exception as exc:
        checks.append(check("runtime_import_and_trace", False, f"{type(exc).__name__}: {exc}"))

    failed = [c for c in checks if not c[1]]
    print("Runtime Orchestration & Observability Doctor")
    print("=" * 64)
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"\nOverall status: {'PASS' if not failed else 'FAIL'}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
