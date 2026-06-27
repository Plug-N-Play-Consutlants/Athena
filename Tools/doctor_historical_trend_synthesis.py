"""
Athena Sports Intelligence Platform

Epic 4D.3d Doctor

Historical Trend Synthesis
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import Core.version as core_version
import Knowledge.Historical.version as historical_version

from Knowledge.Historical.synthesis_engine import (
    build_historical_trend_synthesis,
    historical_trend_signals_for_entity,
)


def _check(checks: list[dict[str, Any]], name: str, condition: bool, detail: Any = "") -> None:
    checks.append({"name": name, "status": "PASS" if condition else "FAIL", "detail": detail})


def run_doctor(project_root: Path | None = None) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    result = build_historical_trend_synthesis(project_root)
    summary = result["summary"]
    signals = result["signals"].get("signals", [])
    comparisons = result["comparisons"].get("comparisons", [])

    sample_entity = signals[0].get("entity_id") if signals else ""
    entity_payload = (
        historical_trend_signals_for_entity(sample_entity, project_root=project_root)
        if sample_entity
        else {"status": "empty"}
    )

    _check(checks, "athena_version_present", bool(core_version.ATHENA_VERSION), core_version.ATHENA_VERSION)
    _check(checks, "summary_version_matches_core", summary.get("athena_version") == core_version.ATHENA_VERSION, summary.get("athena_version"))
    _check(checks, "historical_domain_version_present", bool(historical_version.HISTORICAL_DOMAIN_VERSION), historical_version.HISTORICAL_DOMAIN_VERSION)
    _check(checks, "historical_schema_version_present", bool(historical_version.HISTORICAL_SCHEMA_VERSION), historical_version.HISTORICAL_SCHEMA_VERSION)
    _check(checks, "historical_engine_version_present", bool(historical_version.HISTORICAL_ENGINE_VERSION), historical_version.HISTORICAL_ENGINE_VERSION)
    _check(checks, "historical_synthesis_version_present", bool(historical_version.HISTORICAL_SYNTHESIS_VERSION), historical_version.HISTORICAL_SYNTHESIS_VERSION)
    _check(checks, "summary_synthesis_version_matches_constant", summary.get("historical_synthesis_version") == historical_version.HISTORICAL_SYNTHESIS_VERSION, summary.get("historical_synthesis_version"))
    _check(checks, "summary_status_valid", summary.get("status") in {"ready", "insufficient_data"}, summary.get("status"))
    _check(checks, "comparisons_available", len(comparisons) > 0, len(comparisons))
    _check(checks, "signal_count_matches", summary.get("signal_count") == len(signals), summary.get("signal_count"))
    _check(checks, "signals_generated_or_explained", len(signals) > 0 or len(comparisons) == 0, {"signals": len(signals), "comparisons": len(comparisons)})

    if signals:
        sample = signals[0]
        _check(checks, "sample_signal_has_entity", bool(sample.get("entity_id")), sample.get("entity_id"))
        _check(checks, "sample_signal_has_direction", sample.get("direction") in {"improving", "declining", "stable", "mixed", "unknown"}, sample.get("direction"))
        _check(checks, "sample_signal_confidence_normalized", 0.0 <= float(sample.get("confidence", 0.0)) <= 1.0, sample.get("confidence"))
        _check(checks, "sample_signal_has_evidence", len(sample.get("evidence_comparison_ids", [])) > 0, sample.get("evidence_comparison_ids", [])[:3])
        _check(checks, "entity_lookup_available", entity_payload.get("status") == "available", entity_payload)

    failed = [check for check in checks if check["status"] != "PASS"]

    return {
        "doctor": "historical_trend_synthesis",
        "overall_status": "PASS" if not failed else "FAIL",
        "passed": len(checks) - len(failed),
        "failed": len(failed),
        "checks": checks,
    }


def main() -> int:
    report = run_doctor(PROJECT_ROOT)
    print("Historical Trend Synthesis Doctor")
    print("=" * 45)
    print(f"Overall status: {report['overall_status']}")
    print(f"Passed: {report['passed']}")
    print(f"Failed: {report['failed']}")
    print()
    for check in report["checks"]:
        print(f"[{check['status']}] {check['name']}: {check['detail']}")
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
