"""Validation for v0.5.5.5.0 Runtime Orchestration & Observability."""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("ATHENA_SCOUT_LIVE_NETWORK", "0")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def record(results: list[tuple[str,bool,str]], name: str, condition: bool, detail: str = "") -> None:
    results.append((name, bool(condition), detail))


def main() -> int:
    results: list[tuple[str,bool,str]] = []
    from Core.version import ATHENA_VERSION, ATHENA_BUILD, RELEASE_NAME
    from Intelligence.Runtime import (
        RUNTIME_ORCHESTRATION_VERSION,
        RuntimeStage,
        RuntimeTrace,
        normalize_contributions,
        run_runtime_trace,
        studio_runtime_observability_diagnostics,
    )

    record(results, "athena_version", ATHENA_VERSION.startswith("0.5.5.5"), ATHENA_VERSION)
    record(results, "athena_build", ATHENA_BUILD.startswith("0.5.5.5"), ATHENA_BUILD)
    record(results, "release_name_available", bool(RELEASE_NAME), RELEASE_NAME)
    record(results, "runtime_version", RUNTIME_ORCHESTRATION_VERSION.startswith("0.5.5.5"), RUNTIME_ORCHESTRATION_VERSION)

    stage = RuntimeStage(name="test", status="pass", contributed=True, metrics={"x": 1})
    record(results, "runtime_stage_dict", stage.to_dict()["metrics"]["x"] == 1, str(stage.to_dict()))

    ledger = normalize_contributions({"identity": 2, "live": 1})
    record(results, "ledger_normalizes", abs(sum(item.contribution for item in ledger) - 1.0) < 0.0001, str([x.to_dict() for x in ledger]))

    queries = [
        "Who is Auston Matthews?",
        "What recent NHL events are available?",
        "Compare Auston Matthews and Connor McDavid.",
        "What can Athena currently answer?",
    ]
    for query in queries:
        trace = run_runtime_trace(query)
        data = trace.to_dict()
        record(results, f"trace_created:{query[:20]}", isinstance(trace, RuntimeTrace), data.get("status", ""))
        record(results, f"trace_stage_count:{query[:20]}", data["stage_count"] >= 5, str(data["stage_count"]))
        record(results, f"trace_no_failures:{query[:20]}", data["failed_stage_count"] == 0, str(data["failed_stage_count"]))
        record(results, f"trace_response:{query[:20]}", bool(data["response_summary"]), data["response_summary"])
        record(results, f"trace_ledger:{query[:20]}", len(data["evidence_ledger"]) >= 1, str(data["evidence_ledger"]))

    diag = studio_runtime_observability_diagnostics()
    record(results, "studio_panel", diag.get("panel") == "runtime_orchestration_observability", str(diag.get("panel")))
    record(results, "studio_samples", diag.get("sample_count") == 4, str(diag.get("sample_count")))
    record(results, "studio_no_failed_traces", all(t.get("failed_stage_count") == 0 for t in diag.get("traces", [])), str(diag.get("status")))
    record(results, "supports_observability", "stage timing" in diag.get("supports", []), str(diag.get("supports", [])))

    failed = [r for r in results if not r[1]]
    print("Runtime Orchestration & Observability Validation")
    print("=" * 64)
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"\nOverall status: {'PASS' if not failed else 'FAIL'}")
    print(f"Passed: {len(results)-len(failed)}")
    print(f"Failed: {len(failed)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
