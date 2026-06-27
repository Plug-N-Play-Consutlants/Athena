"""Validate Trend Engine.

Version assertions are consistency-based instead of hard-coded to a single drop.
"""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import Core.version as core_version
from Knowledge.Graph.temporal_intelligence import build_temporal_evidence
import Knowledge.Trends.version as trend_version
import Knowledge.Trends.confidence_engine as confidence_engine
from Knowledge.Trends import (
    TrendDirection,
    build_trend_intelligence,
    build_trend_series,
    calculate_trend_result,
    get_trend_registry,
    observations_from_temporal_events,
    trends_for_entity,
)
from Tools.doctor_trend_engine import run_doctor


def _present(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def main() -> int:
    checks = []

    def check(name: str, ok: bool, detail: object = "") -> None:
        checks.append((name, ok, str(detail)[:1400]))

    temporal = build_temporal_evidence(PROJECT_ROOT)
    timeline = temporal.get("timeline", {})
    obs_payload = observations_from_temporal_events(timeline.get("events", []))
    observations = obs_payload.get("observations", [])
    series = build_trend_series(observations)
    result = build_trend_intelligence(PROJECT_ROOT)
    summary = result.get("summary", {})
    trends = result.get("results", {}).get("trends", [])
    results = result.get("results", {}).get("results", [])
    first_entity = trends[0].get("entity_id") if trends else ""
    entity_payload = trends_for_entity(first_entity, project_root=PROJECT_ROOT) if first_entity else {"status": "empty"}
    doctor = run_doctor(PROJECT_ROOT)
    registry = get_trend_registry()

    check("athena_version_present", _present(core_version.ATHENA_VERSION), core_version.ATHENA_VERSION)
    check("summary_athena_version_matches_core", summary.get("athena_version") == core_version.ATHENA_VERSION, summary.get("athena_version"))
    check("trend_domain_version_present", _present(trend_version.TREND_DOMAIN_VERSION), trend_version.TREND_DOMAIN_VERSION)
    check("trend_engine_version_present", _present(trend_version.TREND_ENGINE_VERSION), trend_version.TREND_ENGINE_VERSION)
    check("trend_schema_version", trend_version.TREND_SCHEMA_VERSION == "trend-schema-v1", trend_version.TREND_SCHEMA_VERSION)
    check("comparison_engine_version_present", _present(trend_version.COMPARISON_ENGINE_VERSION), trend_version.COMPARISON_ENGINE_VERSION)
    check("confidence_engine_version_present", _present(confidence_engine.CONFIDENCE_ENGINE_VERSION), confidence_engine.CONFIDENCE_ENGINE_VERSION)
    check("summary_trend_engine_version_matches_constant", summary.get("trend_engine_version") == trend_version.TREND_ENGINE_VERSION, summary.get("trend_engine_version"))
    check("summary_confidence_engine_version_matches_constant", summary.get("confidence_engine_version") in (None, confidence_engine.CONFIDENCE_ENGINE_VERSION), summary.get("confidence_engine_version"))
    check("temporal_events_available", timeline.get("event_count", 0) > 0, timeline.get("event_count"))
    check("observations_generated", len(observations) > 0, len(observations))
    check("skipped_payload_present", isinstance(obs_payload.get("skipped"), list), obs_payload.get("skipped", [])[:3])
    check("series_generated", len(series) > 0, len(series))
    check("series_have_metric", all(getattr(item, "metric", None) is not None for item in series[:25]), series[:1])
    check("series_have_observations", all(item.observation_count > 0 for item in series[:25]), [item.to_dict() for item in series[:1]])
    check("comparison_engine_version", trend_version.COMPARISON_ENGINE_VERSION == "4D.2-drop3-window-analysis", trend_version.COMPARISON_ENGINE_VERSION)
    calculated = calculate_trend_result(series[0]) if series else None
    check("result_calculates", bool(calculated) and calculated.entity_id == series[0].entity_id, series[0].id if series else "")
    check("engine_summary_ready", summary.get("status") == "ready", summary)
    check("engine_counts_match", summary.get("trend_count") == len(trends) == len(results), summary)
    check("metrics_summary_present", bool(summary.get("metrics")), summary.get("metrics"))
    check("directions_summary_present", bool(summary.get("directions")), summary.get("directions"))
    check("confidence_normalized", all(0.0 <= float(r.get("confidence", 0.0)) <= 1.0 for r in results[:50]), results[:1])
    check("momentum_normalized", all(-1.0 <= float(r.get("momentum_score", 0.0)) <= 1.0 for r in results[:50]), results[:1])
    check("known_gaps_available", all("known_gaps" in r for r in results[:50]), results[:1])
    check("results_include_comparison_engine", all("comparison_engine" in r.get("properties", {}) for r in results[:50]), results[:1])
    check("results_include_confidence_engine", all("confidence_engine" in r.get("properties", {}) for r in results[:50]), results[:1])
    check("results_include_explainability", all("confidence_explanation" in r.get("properties", {}) for r in results[:50]), results[:1])
    check("entity_trends_lookup", entity_payload.get("status") == "available", entity_payload)
    check("registry_validates_generated_result", bool(results) and registry.validate_result(calculate_trend_result(series[0])).get("status") == "valid", results[:1])
    check("direction_values_canonical", all(r.get("direction") in {d.value for d in TrendDirection} for r in results[:50]), results[:1])
    check("doctor_validation_passes", doctor.get("overall_status") == "PASS", doctor)

    passed = sum(1 for _, ok, _ in checks if ok)
    failed = len(checks) - passed
    print("Trend Engine Validation Report")
    print("==============================")
    print(f"Overall status: {'PASS' if failed == 0 else 'FAIL'}")
    print(f"Passed: {passed}")
    print("Warnings: 0")
    print(f"Failed: {failed}")
    print()
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
