"""Athena 4D.4 Historical Intelligence Doctor."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import Core.version as core_version
from Knowledge.Historical.intelligence import HISTORICAL_INTELLIGENCE_VERSION
from Knowledge.Historical.intelligence_engine import build_historical_intelligence_signals, historical_intelligence_for_entity


def _check(checks: list[dict[str, Any]], name: str, condition: bool, detail: Any = "") -> None:
    checks.append({"name": name, "status": "PASS" if condition else "FAIL", "detail": detail})


def run_doctor(project_root: Path | None = None) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    result = build_historical_intelligence_signals(project_root)
    summary = result["summary"]
    signals = result["intelligence"].get("signals", [])
    sample = signals[0] if signals else {}
    entity_payload = historical_intelligence_for_entity(sample.get("entity_id", ""), project_root=project_root) if sample else {"status": "empty"}

    _check(checks, "athena_version_present", bool(core_version.ATHENA_VERSION), core_version.ATHENA_VERSION)
    _check(checks, "intelligence_version_present", bool(HISTORICAL_INTELLIGENCE_VERSION), HISTORICAL_INTELLIGENCE_VERSION)
    _check(checks, "summary_version_matches_core", summary.get("athena_version") == core_version.ATHENA_VERSION, summary.get("athena_version"))
    _check(checks, "summary_intelligence_version_matches_constant", summary.get("historical_intelligence_version") == HISTORICAL_INTELLIGENCE_VERSION, summary.get("historical_intelligence_version"))
    _check(checks, "summary_status_ready", summary.get("status") == "ready", summary)
    _check(checks, "source_nodes_available", summary.get("source_node_count", 0) > 0, summary.get("source_node_count"))
    _check(checks, "signals_generated", len(signals) > 0, len(signals))
    _check(checks, "signal_count_matches", summary.get("signal_count") == len(signals), summary.get("signal_count"))
    _check(checks, "patterns_present", bool(summary.get("patterns")), summary.get("patterns"))
    _check(checks, "directions_present", bool(summary.get("directions")), summary.get("directions"))
    if sample:
        _check(checks, "sample_signal_has_evidence", len(sample.get("evidence_node_ids", [])) > 0, sample.get("evidence_node_ids"))
        _check(checks, "sample_signal_confidence_normalized", 0.0 <= float(sample.get("confidence", 0.0)) <= 1.0, sample.get("confidence"))
        _check(checks, "entity_lookup_available", entity_payload.get("status") == "available", entity_payload)

    failed = [check for check in checks if check["status"] != "PASS"]
    return {"doctor": "historical_intelligence", "overall_status": "PASS" if not failed else "FAIL", "passed": len(checks)-len(failed), "failed": len(failed), "checks": checks}


def main() -> int:
    report = run_doctor(PROJECT_ROOT)
    print("Historical Intelligence Doctor")
    print("=" * 40)
    print(f"Overall status: {report['overall_status']}")
    print(f"Passed: {report['passed']}")
    print(f"Failed: {report['failed']}")
    print()
    for check in report["checks"]:
        print(f"[{check['status']}] {check['name']}: {check['detail']}")
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
