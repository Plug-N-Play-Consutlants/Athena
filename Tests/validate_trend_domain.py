"""Validate Epic 4D.2 Drop 1 canonical trend domain."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_VERSION
from Knowledge.Trends import (
    TREND_DOMAIN_VERSION,
    TREND_SCHEMA_VERSION,
    Trend,
    TrendDirection,
    TrendMetric,
    TrendObservation,
    TrendResult,
    TrendSeries,
    TrendStrength,
    TrendType,
    TrendValueKind,
    TrendWindow,
    TrendWindowType,
    canonical_trend_metrics,
    confidence_band,
    get_trend_registry,
    serialize_trends,
)
from Tools.doctor_trend_domain import run_doctor


def main() -> int:
    checks = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ok, detail))

    registry = get_trend_registry()
    metrics = canonical_trend_metrics()

    check("trend_domain_version", TREND_DOMAIN_VERSION == "4D.2-drop1-trend-domain", TREND_DOMAIN_VERSION)
    check("trend_schema_version", TREND_SCHEMA_VERSION == "trend-schema-v1", TREND_SCHEMA_VERSION)
    check("registry_has_metrics", len(registry.keys()) >= 5, str(registry.keys()))
    check("canonical_metrics_match_registry", set(metrics.keys()).issubset(set(registry.keys())), str(metrics.keys()))
    check("metric_lookup", registry.require("production_points").trend_type == TrendType.PERFORMANCE, registry.require("production_points").to_dict())
    check("by_type_query", len(registry.by_type(TrendType.CONTRACT)) >= 1, str([m.key for m in registry.by_type(TrendType.CONTRACT)]))

    custom_metric = TrendMetric(
        key="custom_signal",
        label="Custom Signal",
        trend_type=TrendType.GENERIC,
        value_kind=TrendValueKind.NUMERIC,
    )
    registry.register(custom_metric)
    check("registry_registers_custom_metric", registry.require("custom_signal").label == "Custom Signal", registry.require("custom_signal").to_dict())

    obs = TrendObservation(
        id="obs:1",
        entity_id="player:003kg",
        metric_key="production_points",
        value=88,
        observed_at="2026-06-20T00:00:00+00:00",
        source_event_id="temporal_event:1",
        confidence=-5,
    )
    check("observation_clamps_confidence_low", obs.confidence == 0.0, obs.to_dict())
    check("observation_serialization_stable", obs.to_dict()["source_event_id"] == "temporal_event:1", obs.to_dict())

    window = TrendWindow(window_type=TrendWindowType.MEDIUM, label="medium", observation_count=2)
    series = TrendSeries(
        id="series:player_003kg:production_points",
        entity_id="player:003kg",
        metric=registry.require("production_points"),
        observations=[obs],
        window=window,
        confidence=0.6,
        source_event_ids=["temporal_event:1"],
    )
    check("series_observation_count", series.observation_count == 1, series.to_dict())
    check("series_serializes_nested_metric", series.to_dict()["metric"]["key"] == "production_points", series.to_dict())

    result = TrendResult(
        id="trend_result:player_003kg:production_points",
        entity_id="player:003kg",
        trend_type=TrendType.PERFORMANCE,
        metric_key="production_points",
        direction=TrendDirection.STABLE,
        strength=TrendStrength.WEAK,
        confidence=0.61,
        momentum_score=-2,
        window=window,
        observation_count=series.observation_count,
        evidence_event_ids=series.source_event_ids,
        explanation="Canonical trend-domain result object.",
    )
    check("result_confidence_band_derived", result.confidence_band.value == "medium", result.to_dict())
    check("result_momentum_clamped", result.momentum_score == -1.0, result.to_dict())
    check("result_validation", registry.validate_result(result)["status"] == "valid", registry.validate_result(result))

    trend = Trend(
        id="trend:player_003kg:production_points",
        entity_id="player:003kg",
        trend_type=TrendType.PERFORMANCE,
        label="Patrick Kane production trend",
        result=result,
        source_series_ids=[series.id],
    )
    check("trend_wrapper_serializes", trend.to_dict()["result"]["metric_key"] == "production_points", trend.to_dict())
    check("serialize_trends_helper", len(serialize_trends([trend, result])) == 2, str(serialize_trends([trend, result])[:1]))
    check("confidence_band_helper_high", confidence_band(0.95).value == "high", confidence_band(0.95).value)
    check("confidence_band_helper_insufficient", confidence_band(0).value == "insufficient", confidence_band(0).value)

    invalid = TrendResult(
        id="trend_result:invalid",
        entity_id="player:003kg",
        trend_type=TrendType.GENERIC,
        metric_key="missing_metric",
    )
    check("registry_rejects_unknown_metric", registry.validate_result(invalid)["status"] == "invalid", registry.validate_result(invalid))

    doctor = run_doctor(PROJECT_ROOT)
    check("doctor_validation_passes", doctor.get("overall_status") == "PASS", str(doctor))
    check("version_current", ATHENA_VERSION == "0.5.0-drop4d2a", f"Athena={ATHENA_VERSION}")

    passed = sum(1 for _, ok, _ in checks)
    failed = len(checks) - passed
    print("Trend Domain Validation Report")
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
