"""Canonical trend registry.

The registry defines Athena's provider-agnostic trend vocabulary. It does not
calculate trends; it only declares which metrics may be used by later analytical
layers.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from Knowledge.Trends.enums import TrendType, TrendValueKind
from Knowledge.Trends.models import TrendMetric, TrendResult


def canonical_trend_metrics() -> Dict[str, TrendMetric]:
    """Return the built-in trend metrics for the first Trend Intelligence drop."""

    metrics = [
        TrendMetric(
            key="production_points",
            label="Production Points",
            trend_type=TrendType.PERFORMANCE,
            value_kind=TrendValueKind.NUMERIC,
            unit="points",
            higher_is_better=True,
            description="Point-production observation derived from temporal production evidence.",
            source_event_types=["production_snapshot"],
        ),
        TrendMetric(
            key="contract_years_remaining",
            label="Contract Years Remaining",
            trend_type=TrendType.CONTRACT,
            value_kind=TrendValueKind.NUMERIC,
            unit="years",
            higher_is_better=None,
            description="Contract runway observation derived from temporal contract evidence.",
            source_event_types=["contract_snapshot"],
        ),
        TrendMetric(
            key="asset_movement_count",
            label="Asset Movement Count",
            trend_type=TrendType.ORGANIZATIONAL,
            value_kind=TrendValueKind.NUMERIC,
            unit="events",
            higher_is_better=None,
            description="Movement/transaction frequency derived from asset movement evidence.",
            source_event_types=["asset_movement", "transaction"],
        ),
        TrendMetric(
            key="availability_status",
            label="Availability Status",
            trend_type=TrendType.AVAILABILITY,
            value_kind=TrendValueKind.CATEGORICAL,
            unit="status",
            higher_is_better=None,
            description="Availability state derived from health or roster-status evidence.",
            source_event_types=["availability_snapshot", "injury_snapshot"],
        ),
        TrendMetric(
            key="role_signal",
            label="Role Signal",
            trend_type=TrendType.ROLE,
            value_kind=TrendValueKind.MIXED,
            unit="signal",
            higher_is_better=None,
            description="Generic deployment or role evidence signal.",
            source_event_types=["role_snapshot", "deployment_snapshot"],
        ),
        TrendMetric(
            key="knowledge_pack_presence",
            label="Knowledge Pack Presence",
            trend_type=TrendType.KNOWLEDGE,
            value_kind=TrendValueKind.BOOLEAN,
            unit="present",
            higher_is_better=True,
            description="Knowledge-pack availability over time.",
            source_event_types=["knowledge_pack_snapshot"],
        ),
    ]
    return {metric.key: metric for metric in metrics}


class TrendRegistry:
    """Small deterministic registry for canonical trend metrics."""

    def __init__(self, metrics: Optional[Iterable[TrendMetric]] = None) -> None:
        self._metrics: Dict[str, TrendMetric] = canonical_trend_metrics()
        if metrics:
            for metric in metrics:
                self.register(metric)

    def register(self, metric: TrendMetric) -> None:
        if not metric.key:
            raise ValueError("TrendMetric.key is required")
        self._metrics[metric.key] = metric

    def get(self, key: str) -> Optional[TrendMetric]:
        return self._metrics.get(key)

    def require(self, key: str) -> TrendMetric:
        metric = self.get(key)
        if metric is None:
            raise KeyError(f"Unknown trend metric: {key}")
        return metric

    def keys(self) -> List[str]:
        return sorted(self._metrics.keys())

    def metrics(self) -> List[TrendMetric]:
        return [self._metrics[key] for key in self.keys()]

    def by_type(self, trend_type: TrendType | str) -> List[TrendMetric]:
        value = trend_type.value if hasattr(trend_type, "value") else str(trend_type)
        return [metric for metric in self.metrics() if metric.trend_type.value == value]

    def validate_result(self, result: TrendResult) -> Dict[str, Any]:
        issues: List[str] = []
        metric = self.get(result.metric_key)
        if metric is None:
            issues.append(f"Unknown metric_key: {result.metric_key}")
        if result.entity_id == "":
            issues.append("entity_id is required")
        if result.observation_count < 0:
            issues.append("observation_count cannot be negative")
        if result.confidence < 0.0 or result.confidence > 1.0:
            issues.append("confidence must be normalized")
        return {
            "status": "valid" if not issues else "invalid",
            "issues": issues,
            "metric": metric.to_dict() if metric else None,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_count": len(self._metrics),
            "metrics": [metric.to_dict() for metric in self.metrics()],
        }


def get_trend_registry() -> TrendRegistry:
    return TrendRegistry()
