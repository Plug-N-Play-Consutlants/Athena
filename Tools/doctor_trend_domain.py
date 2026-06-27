"""Doctor for Epic 4D.2 Drop 1 canonical trend domain."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_VERSION
from Knowledge.Trends import (
    TREND_DOMAIN_VERSION,
    TREND_SCHEMA_VERSION,
    TrendDirection,
    TrendObservation,
    TrendResult,
    TrendStrength,
    TrendType,
    TrendWindow,
    TrendWindowType,
    confidence_band,
    get_trend_registry,
    trend_metadata,
)


def run_doctor(project_root: Path | None = None) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    def check(name: str, ok: bool, detail: Any = "") -> None:
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": str(detail)[:600]})

    registry = get_trend_registry()
    metadata = trend_metadata()

    check("trend_domain_version_current", TREND_DOMAIN_VERSION == "4D.2-drop1-trend-domain", TREND_DOMAIN_VERSION)
    check("trend_schema_version_present", TREND_SCHEMA_VERSION == "trend-schema-v1", TREND_SCHEMA_VERSION)
    check("metadata_available", metadata.get("principle") == "trends_are_derived_from_temporal_evidence", metadata)
    check("registry_available", registry.to_dict().get("metric_count", 0) >= 5, registry.to_dict())
    check("canonical_metrics_present", {"production_points", "contract_years_remaining", "asset_movement_count"}.issubset(set(registry.keys())), registry.keys())
    check("performance_metrics_queryable", len(registry.by_type(TrendType.PERFORMANCE)) >= 1, [m.key for m in registry.by_type(TrendType.PERFORMANCE)])

    observation = TrendObservation(
        id="trend_observation:sample",
        entity_id="player:sample",
        metric_key="production_points",
        value=42,
        observed_at="2026-06-20T00:00:00+00:00",
        source_event_id="temporal_event:sample",
        confidence=1.25,
    )
    check("observation_confidence_clamped", observation.confidence == 1.0, observation.to_dict())
    check("observation_serializes", observation.to_dict().get("metric_key") == "production_points", observation.to_dict())

    window = TrendWindow(window_type=TrendWindowType.SHORT, label="short", observation_count=1)
    result = TrendResult(
        id="trend:sample",
        entity_id="player:sample",
        trend_type=TrendType.PERFORMANCE,
        metric_key="production_points",
        direction=TrendDirection.RISING,
        strength=TrendStrength.MODERATE,
        confidence=0.82,
        momentum_score=1.7,
        window=window,
        observation_count=1,
        evidence_event_ids=["temporal_event:sample"],
        explanation="Sample deterministic trend-domain object.",
    )
    check("result_confidence_band", result.confidence_band.value == "high", result.to_dict())
    check("momentum_clamped", result.momentum_score == 1.0, result.to_dict())
    check("result_serializes_enums", result.to_dict().get("direction") == "rising", result.to_dict())
    check("registry_validates_result", registry.validate_result(result).get("status") == "valid", registry.validate_result(result))
    check("confidence_band_helper", confidence_band(0.6).value == "medium", confidence_band(0.6))
    check("version_current", ATHENA_VERSION == "0.5.0-drop4d2a", f"Athena={ATHENA_VERSION}")

    failed = sum(1 for item in checks if item["status"] != "PASS")
    return {
        "doctor": "trend_domain",
        "overall_status": "PASS" if failed == 0 else "FAIL",
        "passed": len(checks) - failed,
        "failed": failed,
        "checks": checks,
    }


if __name__ == "__main__":
    result = run_doctor()
    print("Trend Domain Doctor")
    print("===================")
    print(f"Overall status: {result['overall_status']}")
    print(f"Passed: {result['passed']}")
    print(f"Failed: {result['failed']}")
    print()
    for item in result["checks"]:
        print(f"[{item['status']}] {item['name']}: {item['detail']}")
    raise SystemExit(0 if result["overall_status"] == "PASS" else 1)
