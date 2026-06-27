"""Doctor for Trend Engine.

Version checks are consistency-based rather than hard-coded to a historical drop.
This keeps the doctor stable across small Athena version bumps.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import Core.version as core_version
from Knowledge.Trends import build_trend_intelligence, trends_for_entity
import Knowledge.Trends.version as trend_version
import Knowledge.Trends.confidence_engine as confidence_engine


def _version_present(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def run_doctor(project_root: Path | None = None) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    def check(name: str, ok: bool, detail: Any = "") -> None:
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": str(detail)[:900]})

    result = build_trend_intelligence(project_root)
    summary = result.get("summary", {})
    trends = result.get("results", {}).get("trends", [])
    series = result.get("series", {}).get("series", [])
    first_entity = trends[0].get("entity_id") if trends else None
    entity_payload = trends_for_entity(first_entity, project_root=project_root) if first_entity else {"status": "empty"}

    check("athena_version_present", _version_present(core_version.ATHENA_VERSION), core_version.ATHENA_VERSION)
    check("summary_athena_version_matches_core", summary.get("athena_version") == core_version.ATHENA_VERSION, summary.get("athena_version"))
    check("trend_domain_version_present", _version_present(trend_version.TREND_DOMAIN_VERSION), trend_version.TREND_DOMAIN_VERSION)
    check("trend_engine_version_present", _version_present(trend_version.TREND_ENGINE_VERSION), trend_version.TREND_ENGINE_VERSION)
    check("trend_schema_version_present", trend_version.TREND_SCHEMA_VERSION == "trend-schema-v1", trend_version.TREND_SCHEMA_VERSION)
    check("comparison_engine_version_present", _version_present(trend_version.COMPARISON_ENGINE_VERSION), trend_version.COMPARISON_ENGINE_VERSION)
    check("confidence_engine_version_present", _version_present(confidence_engine.CONFIDENCE_ENGINE_VERSION), confidence_engine.CONFIDENCE_ENGINE_VERSION)
    check("summary_trend_engine_version_matches_constant", summary.get("trend_engine_version") == trend_version.TREND_ENGINE_VERSION, summary.get("trend_engine_version"))
    check("summary_confidence_engine_version_matches_constant", summary.get("confidence_engine_version") in (None, confidence_engine.CONFIDENCE_ENGINE_VERSION), summary.get("confidence_engine_version"))
    check("engine_status_ready", summary.get("status") == "ready", summary)
    check("observations_generated", summary.get("observation_count", 0) > 0, summary.get("observation_count"))
    check("series_generated", summary.get("series_count", 0) > 0, summary.get("series_count"))
    check("trends_generated", summary.get("trend_count", 0) > 0, summary.get("trend_count"))
    check("series_include_observations", any(item.get("observation_count", 0) > 0 for item in series), series[:1])
    check("results_include_confidence", all("confidence" in trend.get("result", {}) for trend in trends[:20]), trends[:1])
    check("results_include_direction", all("direction" in trend.get("result", {}) for trend in trends[:20]), trends[:1])
    check("results_include_comparison_engine", all("comparison_engine" in trend.get("result", {}).get("properties", {}) for trend in trends[:20]), trends[:1])
    check("results_include_confidence_engine", all("confidence_engine" in trend.get("result", {}).get("properties", {}) for trend in trends[:20]), trends[:1])
    check("metrics_present", bool(summary.get("metrics")), summary.get("metrics"))
    check("entity_lookup_available", entity_payload.get("status") == "available", entity_payload)
    check("output_files_declared", bool(summary.get("series_file")) and bool(summary.get("results_file")), summary)

    failed = [c for c in checks if c["status"] != "PASS"]
    return {
        "doctor": "trend_engine",
        "overall_status": "PASS" if not failed else "FAIL",
        "passed": len(checks) - len(failed),
        "failed": len(failed),
        "checks": checks,
    }


def main() -> int:
    report = run_doctor()
    print("Trend Engine Doctor")
    print("===================")
    print(f"Overall status: {report['overall_status']}")
    print(f"Passed: {report['passed']}")
    print(f"Failed: {report['failed']}")
    print()
    for check in report["checks"]:
        print(f"[{check['status']}] {check['name']}: {check['detail']}")
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
