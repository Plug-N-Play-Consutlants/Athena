"""Epic 4D.2 Drop 2 trend engine.

This module turns 4D.1 temporal evidence into canonical trend-domain objects.
It remains provider-agnostic and sport-agnostic: every trend is derived from
TemporalEvent records and canonical TrendMetric declarations.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, DefaultDict, Dict, Iterable, List, Optional, Tuple

from Core.json_utils import read_optional_json, write_json
from Core.project_paths import OUTPUT_DIR
import Core.version as core_version
from Knowledge.Graph.temporal_intelligence import TIMELINE_FILE, build_temporal_evidence
from Knowledge.Trends.enums import TrendDirection, TrendStrength, TrendValueKind, TrendWindowType
from Knowledge.Trends.models import (
    Trend,
    TrendMetric,
    TrendObservation,
    TrendResult,
    TrendSeries,
    TrendWindow,
    clamp_confidence,
)
from Knowledge.Trends.registry import TrendRegistry, get_trend_registry
import Knowledge.Trends.version as trend_version
from Knowledge.Trends.comparison_engine import ComparisonEngine
import Knowledge.Trends.confidence_engine as confidence_engine

TREND_SERIES_FILE = "trend_series.json"
TREND_RESULTS_FILE = "trend_results.json"
TREND_SUMMARY_FILE = "trend_intelligence_summary.json"
TREND_ENGINE_REPORT_FILE = "trend_engine_report.json"


NUMERIC_PROPERTY_KEYS: Dict[str, List[str]] = {
    "production_points": ["points", "production_points"],
    "contract_years_remaining": ["years_remaining", "contract_years_remaining"],
    "asset_movement_count": ["movement_count", "count"],
    "role_signal": ["role_score", "role_signal"],
}

BOOLEAN_PROPERTY_KEYS: Dict[str, List[str]] = {
    "knowledge_pack_presence": ["source_document_present", "present"],
}

CATEGORICAL_PROPERTY_KEYS: Dict[str, List[str]] = {
    "availability_status": ["availability_status", "injury_status", "status"],
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: Any) -> Optional[float]:
    if value in (None, "", [], {}):
        return None
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _sort_observations(observations: Iterable[TrendObservation]) -> List[TrendObservation]:
    return sorted(observations, key=lambda obs: (obs.observed_at or "9999-12-31T23:59:59+00:00", obs.id))


def _extract_property(properties: Dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in properties and properties.get(key) not in (None, ""):
            return properties.get(key)
    return None


def _value_for_metric(event: Dict[str, Any], metric: TrendMetric) -> Tuple[Any, List[str]]:
    """Extract a metric value from a temporal event.

    Returns (value, gaps). A None value means the event cannot produce a useful
    observation for this metric.
    """

    properties = event.get("properties") if isinstance(event.get("properties"), dict) else {}
    gaps: List[str] = []

    if metric.key == "asset_movement_count":
        return 1, gaps

    if metric.value_kind == TrendValueKind.NUMERIC:
        value = _extract_property(properties, NUMERIC_PROPERTY_KEYS.get(metric.key, []))
        numeric = _safe_float(value)
        if numeric is None and metric.key == "production_points":
            goals = _safe_float(properties.get("goals")) or 0.0
            assists = _safe_float(properties.get("assists")) or 0.0
            if goals or assists:
                numeric = goals + assists
        if numeric is None:
            gaps.append(f"No numeric value found for metric {metric.key} on event {event.get('id')}")
            return None, gaps
        if float(numeric).is_integer():
            return int(numeric), gaps
        return round(numeric, 4), gaps

    if metric.value_kind == TrendValueKind.BOOLEAN:
        value = _extract_property(properties, BOOLEAN_PROPERTY_KEYS.get(metric.key, []))
        if value is None:
            # Presence of a matching event is itself useful boolean evidence.
            return True, gaps
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "present", "available"}, gaps
        return bool(value), gaps

    if metric.value_kind == TrendValueKind.CATEGORICAL:
        value = _extract_property(properties, CATEGORICAL_PROPERTY_KEYS.get(metric.key, []))
        if value is None:
            gaps.append(f"No categorical value found for metric {metric.key} on event {event.get('id')}")
            return None, gaps
        return str(value), gaps

    value = _extract_property(properties, NUMERIC_PROPERTY_KEYS.get(metric.key, []) + CATEGORICAL_PROPERTY_KEYS.get(metric.key, []))
    if value is None:
        return event.get("type"), gaps
    return value, gaps


def _observation_id(entity_id: str, metric_key: str, event_id: str) -> str:
    safe = f"{entity_id}:{metric_key}:{event_id}".replace(":", "_").replace("/", "_")
    return f"trend_observation:{safe}"


def observations_from_temporal_events(
    events: Iterable[Dict[str, Any]],
    *,
    registry: Optional[TrendRegistry] = None,
) -> Dict[str, Any]:
    """Build canonical TrendObservation objects from temporal events."""

    trend_registry = registry or get_trend_registry()
    metrics_by_event_type: DefaultDict[str, List[TrendMetric]] = defaultdict(list)
    for metric in trend_registry.metrics():
        for event_type in metric.source_event_types:
            metrics_by_event_type[event_type].append(metric)

    observations: List[TrendObservation] = []
    skipped: List[Dict[str, Any]] = []

    for event in events:
        if not isinstance(event, dict):
            continue
        event_type = event.get("type")
        subject_id = str(event.get("subject_id") or "")
        if not event_type or not subject_id:
            skipped.append({"event_id": event.get("id"), "reason": "missing event type or subject"})
            continue
        metrics = metrics_by_event_type.get(str(event_type), [])
        if not metrics:
            continue
        for metric in metrics:
            value, gaps = _value_for_metric(event, metric)
            if value is None:
                skipped.append({"event_id": event.get("id"), "metric_key": metric.key, "reason": "; ".join(gaps)})
                continue
            observations.append(TrendObservation(
                id=_observation_id(subject_id, metric.key, str(event.get("id") or len(observations))),
                entity_id=subject_id,
                metric_key=metric.key,
                value=value,
                observed_at=event.get("occurred_at"),
                source_event_id=event.get("id"),
                confidence=event.get("confidence", 0.75),
                properties={
                    "event_type": event_type,
                    "event_label": event.get("label"),
                    "event_source": event.get("source"),
                    "value_kind": metric.value_kind.value,
                },
            ))

    return {
        "observations": _sort_observations(observations),
        "skipped": skipped,
    }


def _window_for_observations(observations: List[TrendObservation], window_type: TrendWindowType) -> TrendWindow:
    dated = [_parse_datetime(obs.observed_at) for obs in observations if obs.observed_at]
    dated = [dt for dt in dated if dt is not None]
    start_at = min(dated).isoformat() if dated else None
    end_at = max(dated).isoformat() if dated else None
    missing = sum(1 for obs in observations if not obs.observed_at)
    return TrendWindow(
        window_type=window_type,
        label=window_type.value,
        start_at=start_at,
        end_at=end_at,
        observation_count=len(observations),
        missing_count=missing,
        properties={"source": "temporal_evidence"},
    )


def build_trend_series(
    observations: Iterable[TrendObservation],
    *,
    registry: Optional[TrendRegistry] = None,
    window_type: TrendWindowType = TrendWindowType.ALL_TIME,
) -> List[TrendSeries]:
    """Group observations into canonical TrendSeries objects."""

    trend_registry = registry or get_trend_registry()
    grouped: DefaultDict[Tuple[str, str], List[TrendObservation]] = defaultdict(list)
    for observation in observations:
        grouped[(observation.entity_id, observation.metric_key)].append(observation)

    series: List[TrendSeries] = []
    for (entity_id, metric_key), obs_list in sorted(grouped.items()):
        metric = trend_registry.get(metric_key)
        if metric is None:
            continue
        ordered = _sort_observations(obs_list)
        confidences = [obs.confidence for obs in ordered]
        source_ids = [obs.source_event_id for obs in ordered if obs.source_event_id]
        confidence = mean(confidences) if confidences else 0.0
        series.append(TrendSeries(
            id=f"trend_series:{entity_id.replace(':', '_')}:{metric_key}",
            entity_id=entity_id,
            metric=metric,
            observations=ordered,
            window=_window_for_observations(ordered, window_type),
            confidence=confidence,
            source_event_ids=sorted(set(source_ids)),
            properties={"trend_engine_version": trend_version.TREND_ENGINE_VERSION},
        ))
    return series


def _numeric_values(series: TrendSeries) -> List[float]:
    values: List[float] = []
    for observation in series.observations:
        number = _safe_float(observation.value)
        if number is not None:
            values.append(number)
    return values


def _classify_strength(momentum: float, observation_count: int) -> TrendStrength:
    magnitude = abs(momentum)
    if observation_count < 2 or magnitude < 0.05:
        return TrendStrength.NONE if magnitude < 0.02 else TrendStrength.WEAK
    if magnitude >= 0.75:
        return TrendStrength.EXTREME
    if magnitude >= 0.45:
        return TrendStrength.STRONG
    if magnitude >= 0.2:
        return TrendStrength.MODERATE
    return TrendStrength.WEAK


def _direction_from_momentum(momentum: float, observation_count: int, *, metric: TrendMetric) -> TrendDirection:
    if observation_count < 2:
        return TrendDirection.INSUFFICIENT_DATA
    if abs(momentum) < 0.05:
        return TrendDirection.STABLE
    return TrendDirection.RISING if momentum > 0 else TrendDirection.DECLINING


def _series_confidence(series: TrendSeries, usable_values: int, missing_values: int) -> float:
    if not series.observations:
        return 0.0
    base = series.confidence
    count_factor = min(1.0, usable_values / 4.0)
    date_factor = 1.0 - min(0.4, (series.window.missing_count if series.window else 0) * 0.05)
    missing_factor = 1.0 - min(0.5, missing_values * 0.1)
    return clamp_confidence((base * 0.55) + (count_factor * 0.3) + (date_factor * 0.1) + (missing_factor * 0.05))


def calculate_trend_result(series: TrendSeries) -> TrendResult:
    """Calculate one deterministic TrendResult from a TrendSeries."""

    metric = series.metric
    known_gaps: List[str] = []
    comparison_package = ComparisonEngine.build(series)
    values = _numeric_values(series)
    missing_values = max(0, len(series.observations) - len(values))

    if metric.value_kind in {TrendValueKind.NUMERIC, TrendValueKind.BOOLEAN}:
        if len(values) < 2:
            direction = TrendDirection.INSUFFICIENT_DATA
            strength = TrendStrength.NONE
            momentum = 0.0
            known_gaps.append("At least two usable numeric observations are required for directional trend analysis.")
        else:
            first = values[0]
            last = values[-1]
            baseline = max(1.0, abs(first))
            raw = (last - first) / baseline
            if metric.higher_is_better is False:
                raw = raw * -1.0
            momentum = round(max(-1.0, min(1.0, raw)), 4)
            direction = _direction_from_momentum(momentum, len(values), metric=metric)
            strength = _classify_strength(momentum, len(values))
        confidence = _series_confidence(series, len(values), missing_values)
    else:
        observed = [obs.value for obs in series.observations if obs.value not in (None, "")]
        unique_values = {str(value) for value in observed}
        if len(observed) < 2:
            direction = TrendDirection.INSUFFICIENT_DATA
            strength = TrendStrength.NONE
            momentum = 0.0
            known_gaps.append("At least two categorical observations are required for stability analysis.")
        elif len(unique_values) == 1:
            direction = TrendDirection.STABLE
            strength = TrendStrength.WEAK
            momentum = 0.0
        else:
            direction = TrendDirection.VOLATILE
            strength = TrendStrength.MODERATE if len(unique_values) == 2 else TrendStrength.STRONG
            momentum = round(min(1.0, len(unique_values) / max(1, len(observed))), 4)
        confidence = _series_confidence(series, len(observed), max(0, len(series.observations) - len(observed)))

    # 4D.2c window/momentum overlay. The original 4D.2b direction remains
    # available in properties while momentum_score is enriched by the comparison engine.
    original_direction = direction
    original_strength = strength
    original_momentum = momentum
    if comparison_package.momentum.direction != TrendDirection.INSUFFICIENT_DATA:
        direction = comparison_package.momentum.direction
        momentum = comparison_package.momentum.score
        strength = _classify_strength(momentum, len(values))

    if series.window and series.window.missing_count:
        known_gaps.append(f"{series.window.missing_count} observation(s) have no timestamp.")

    explanation = (
        f"{metric.label} trend derived from {len(series.observations)} temporal observation(s) "
        f"using {trend_version.TREND_ENGINE_VERSION}. "
        f"Window analysis produced {comparison_package.summary['window_count']} window(s), "
        f"{comparison_package.summary['comparison_count']} comparison(s), "
        f"momentum score {comparison_package.summary['momentum_score']:.3f}."
    )

    base_properties = {
        "trend_engine_version": trend_version.TREND_ENGINE_VERSION,
        "comparison_engine_version": trend_version.COMPARISON_ENGINE_VERSION,
        "value_kind": metric.value_kind.value,
        "higher_is_better": metric.higher_is_better,
        "original_direction": original_direction.value,
        "original_strength": original_strength.value,
        "original_momentum_score": original_momentum,
        "comparison_engine": comparison_package.serialize(),
        "comparison_engine_metadata": ComparisonEngine.metadata(),
    }

    base_result = TrendResult(
        id=f"trend_result:{series.entity_id.replace(':', '_')}:{metric.key}",
        entity_id=series.entity_id,
        trend_type=metric.trend_type,
        metric_key=metric.key,
        direction=direction,
        strength=strength,
        confidence=confidence,
        momentum_score=momentum,
        window=series.window,
        observation_count=len(series.observations),
        evidence_event_ids=series.source_event_ids,
        explanation=explanation,
        known_gaps=known_gaps,
        properties=base_properties,
    )

    confidence_package = confidence_engine.TrendConfidenceEngine.build(series=series, result=base_result)
    confidence_payload = confidence_package.serialize()
    confidence_score = confidence_package.confidence.overall_score
    merged_gaps = []
    for gap in list(base_result.known_gaps or []) + list(confidence_package.confidence.known_gaps or []):
        if gap and gap not in merged_gaps:
            merged_gaps.append(gap)

    enriched_properties = dict(base_result.properties)
    confidence_explanation = confidence_payload.get("explanation", {})

    enriched_properties.update({
        "confidence_engine_version": confidence_engine.CONFIDENCE_ENGINE_VERSION,
        "confidence_engine": confidence_payload,
        "confidence_engine_metadata": confidence_engine.TrendConfidenceEngine.metadata(),
        "confidence": confidence_payload.get("confidence", {}),
        "quality": confidence_payload.get("quality", {}),
        "confidence_explanation": confidence_explanation,
        "explainability": confidence_explanation,
    })

    explanation_suffix = confidence_explanation.get("confidence")
    enriched_explanation = base_result.explanation
    if explanation_suffix:
        enriched_explanation = f"{enriched_explanation} Confidence: {explanation_suffix}."

    return TrendResult(
        id=base_result.id,
        entity_id=base_result.entity_id,
        trend_type=base_result.trend_type,
        metric_key=base_result.metric_key,
        direction=base_result.direction,
        strength=base_result.strength,
        confidence=confidence_score,
        momentum_score=base_result.momentum_score,
        window=base_result.window,
        observation_count=base_result.observation_count,
        evidence_event_ids=base_result.evidence_event_ids,
        explanation=enriched_explanation,
        known_gaps=merged_gaps,
        properties=enriched_properties,
    )


def build_trends_from_series(series_items: Iterable[TrendSeries]) -> List[Trend]:
    trends: List[Trend] = []
    for series in series_items:
        result = calculate_trend_result(series)
        trends.append(Trend(
            id=f"trend:{series.entity_id.replace(':', '_')}:{series.metric.key}",
            entity_id=series.entity_id,
            trend_type=series.metric.trend_type,
            label=f"{series.entity_id} {series.metric.label} trend",
            result=result,
            source_series_ids=[series.id],
            properties={"trend_engine_version": trend_version.TREND_ENGINE_VERSION},
        ))
    return trends


def build_trend_intelligence(project_root: Path | None = None) -> Dict[str, Any]:
    """Build trend observations, series, and results from temporal evidence."""

    root = Path(project_root) if project_root is not None else None
    output_dir = OUTPUT_DIR if root is None else root / "Output"
    timeline_payload = read_optional_json(output_dir / TIMELINE_FILE)
    if not isinstance(timeline_payload, dict) or not isinstance(timeline_payload.get("events"), list):
        timeline_payload = build_temporal_evidence(root)["timeline"]

    observation_payload = observations_from_temporal_events(timeline_payload.get("events", []))
    observations = observation_payload["observations"]
    series = build_trend_series(observations)
    trends = build_trends_from_series(series)
    results = [trend.result for trend in trends]

    series_payload = {
        "athena_version": core_version.ATHENA_VERSION,
        "trend_domain_version": trend_version.TREND_DOMAIN_VERSION,
        "trend_schema_version": trend_version.TREND_SCHEMA_VERSION,
        "trend_engine_version": trend_version.TREND_ENGINE_VERSION,
        "confidence_engine_version": confidence_engine.CONFIDENCE_ENGINE_VERSION,
        "generated_at": _utc_now(),
        "series_count": len(series),
        "observation_count": len(observations),
        "series": [item.to_dict() for item in series],
    }
    results_payload = {
        "athena_version": core_version.ATHENA_VERSION,
        "trend_domain_version": trend_version.TREND_DOMAIN_VERSION,
        "trend_schema_version": trend_version.TREND_SCHEMA_VERSION,
        "trend_engine_version": trend_version.TREND_ENGINE_VERSION,
        "confidence_engine_version": confidence_engine.CONFIDENCE_ENGINE_VERSION,
        "generated_at": _utc_now(),
        "trend_count": len(trends),
        "trends": [trend.to_dict() for trend in trends],
        "results": [result.to_dict() for result in results],
    }

    by_metric: Dict[str, int] = {}
    by_direction: Dict[str, int] = {}
    by_entity: Dict[str, int] = {}
    for result in results:
        by_metric[result.metric_key] = by_metric.get(result.metric_key, 0) + 1
        by_direction[result.direction.value] = by_direction.get(result.direction.value, 0) + 1
        by_entity[result.entity_id] = by_entity.get(result.entity_id, 0) + 1

    summary = {
        "athena_version": core_version.ATHENA_VERSION,
        "trend_domain_version": trend_version.TREND_DOMAIN_VERSION,
        "trend_schema_version": trend_version.TREND_SCHEMA_VERSION,
        "trend_engine_version": trend_version.TREND_ENGINE_VERSION,
        "confidence_engine_version": confidence_engine.CONFIDENCE_ENGINE_VERSION,
        "status": "ready" if trends else "empty",
        "generated_at": _utc_now(),
        "observation_count": len(observations),
        "series_count": len(series),
        "trend_count": len(trends),
        "skipped_observation_count": len(observation_payload["skipped"]),
        "metrics": by_metric,
        "directions": by_direction,
        "entities_with_trends": len(by_entity),
        "series_file": str(output_dir / TREND_SERIES_FILE),
        "results_file": str(output_dir / TREND_RESULTS_FILE),
    }

    write_json(output_dir / TREND_SERIES_FILE, series_payload)
    write_json(output_dir / TREND_RESULTS_FILE, results_payload)
    write_json(output_dir / TREND_SUMMARY_FILE, summary)
    write_json(output_dir / TREND_ENGINE_REPORT_FILE, {"summary": summary, "skipped": observation_payload["skipped"][:250]})

    return {
        "summary": summary,
        "series": series_payload,
        "results": results_payload,
        "skipped": observation_payload["skipped"],
    }


def trends_for_entity(entity_id: str, *, project_root: Path | None = None, limit: int = 20) -> Dict[str, Any]:
    output_dir = OUTPUT_DIR if project_root is None else Path(project_root) / "Output"
    payload = read_optional_json(output_dir / TREND_RESULTS_FILE)
    if not isinstance(payload, dict) or not isinstance(payload.get("trends"), list):
        payload = build_trend_intelligence(project_root)["results"]
    trends = [trend for trend in payload.get("trends", []) if isinstance(trend, dict) and trend.get("entity_id") == entity_id]
    trends = sorted(
        trends,
        key=lambda trend: (
            -float(trend.get("result", {}).get("confidence", 0.0) or 0.0),
            trend.get("id") or "",
        ),
    )[: max(1, int(limit or 20))]
    return {
        "status": "available" if trends else "empty",
        "athena_version": core_version.ATHENA_VERSION,
        "trend_engine_version": trend_version.TREND_ENGINE_VERSION,
        "confidence_engine_version": confidence_engine.CONFIDENCE_ENGINE_VERSION,
        "entity_id": entity_id,
        "trend_count": len(trends),
        "trends": trends,
        "known_gaps": [] if trends else ["No trend results are currently available for the requested entity."],
    }


if __name__ == "__main__":
    result = build_trend_intelligence()
    print("Athena Trend Engine")
    print("===================")
    print(f"Status: {result['summary']['status']}")
    print(f"Observations: {result['summary']['observation_count']}")
    print(f"Series: {result['summary']['series_count']}")
    print(f"Trends: {result['summary']['trend_count']}")
