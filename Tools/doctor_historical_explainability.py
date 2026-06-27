"""
Athena Sports Intelligence Platform

Epic 4D.3e Doctor

Historical Signal Explainability
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import Core.version as core_version
from Knowledge.Historical.confidence_engine import (
    HISTORICAL_CONFIDENCE_ENGINE_VERSION,
    HistoricalExplainabilityEngine,
)
from Knowledge.Historical.explainability import HISTORICAL_EXPLAINABILITY_VERSION
from Knowledge.Historical.synthesis_engine import build_historical_trend_synthesis


def _check(checks: list[dict[str, Any]], name: str, condition: bool, detail: Any = "") -> None:
    checks.append({"name": name, "status": "PASS" if condition else "FAIL", "detail": detail})


def run_doctor(project_root: Path | None = None) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    synthesis = build_historical_trend_synthesis(project_root)
    summary = synthesis["summary"]
    signals = synthesis["signals"].get("signals", [])
    sample_signal = signals[0] if signals else {}
    package = HistoricalExplainabilityEngine.build(sample_signal) if sample_signal else None
    payload = package.to_dict() if package else {}

    _check(checks, "athena_version_present", bool(core_version.ATHENA_VERSION), core_version.ATHENA_VERSION)
    _check(checks, "synthesis_status_ready", summary.get("status") == "ready", summary.get("status"))
    _check(checks, "signals_available", len(signals) > 0, len(signals))
    _check(checks, "confidence_engine_version_present", bool(HISTORICAL_CONFIDENCE_ENGINE_VERSION), HISTORICAL_CONFIDENCE_ENGINE_VERSION)
    _check(checks, "explainability_version_present", bool(HISTORICAL_EXPLAINABILITY_VERSION), HISTORICAL_EXPLAINABILITY_VERSION)
    _check(checks, "confidence_package_present", "confidence" in payload, payload.keys())
    _check(checks, "explanation_package_present", "explanation" in payload, payload.keys())

    confidence = payload.get("confidence", {})
    explanation = payload.get("explanation", {})

    _check(checks, "confidence_score_normalized", 0.0 <= float(confidence.get("score", -1)) <= 1.0, confidence.get("score"))
    _check(checks, "confidence_band_present", bool(confidence.get("band")), confidence.get("band"))
    _check(checks, "explanation_summary_present", bool(explanation.get("summary")), explanation.get("summary"))
    _check(checks, "explanation_evidence_present", len(explanation.get("evidence", [])) > 0, explanation.get("evidence", []))

    metadata = HistoricalExplainabilityEngine.metadata()
    _check(checks, "metadata_available", metadata.get("historical_confidence_engine_version") == HISTORICAL_CONFIDENCE_ENGINE_VERSION, metadata)

    failed = [check for check in checks if check["status"] != "PASS"]
    return {
        "doctor": "historical_explainability",
        "overall_status": "PASS" if not failed else "FAIL",
        "passed": len(checks) - len(failed),
        "failed": len(failed),
        "checks": checks,
    }


def main() -> int:
    report = run_doctor(PROJECT_ROOT)
    print("Historical Signal Explainability Doctor")
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
