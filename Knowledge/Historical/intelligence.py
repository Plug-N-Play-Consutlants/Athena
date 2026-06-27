"""
Athena Sports Intelligence Platform

Epic 4D.4

Historical Intelligence Synthesizer

Consumes historical graph bridge nodes and emits higher-order historical
intelligence signals.
"""

from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Any, DefaultDict

from .intelligence_models import (
    HistoricalIntelligenceDirection,
    HistoricalIntelligenceSignal,
    HistoricalIntelligenceStrength,
    HistoricalPatternType,
)

HISTORICAL_INTELLIGENCE_VERSION = "4D.4-historical-intelligence"


def _safe_id(value: str) -> str:
    return str(value).replace(":", "_").replace("/", "_").replace(" ", "_")


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _direction_from_counts(change_counts: dict[str, int], fallback: str) -> HistoricalIntelligenceDirection:
    improved = int(change_counts.get("improved", 0) or 0)
    declined = int(change_counts.get("declined", 0) or 0)
    stable = int(change_counts.get("stable", 0) or 0)
    unknown = int(change_counts.get("unknown", 0) or 0)

    if improved > declined and improved >= stable:
        return HistoricalIntelligenceDirection.IMPROVING
    if declined > improved and declined >= stable:
        return HistoricalIntelligenceDirection.DECLINING
    if stable > 0 and stable >= improved and stable >= declined:
        return HistoricalIntelligenceDirection.STABLE
    if unknown > 0:
        return HistoricalIntelligenceDirection.UNKNOWN

    if fallback == "improved":
        return HistoricalIntelligenceDirection.IMPROVING
    if fallback == "declined":
        return HistoricalIntelligenceDirection.DECLINING
    if fallback == "stable":
        return HistoricalIntelligenceDirection.STABLE
    return HistoricalIntelligenceDirection.UNKNOWN


def _strength_from_confidence_and_count(confidence: float, count: int) -> HistoricalIntelligenceStrength:
    if count <= 0 or confidence < 0.35:
        return HistoricalIntelligenceStrength.NONE
    if confidence >= 0.80 and count >= 3:
        return HistoricalIntelligenceStrength.STRONG
    if confidence >= 0.60 and count >= 2:
        return HistoricalIntelligenceStrength.MODERATE
    return HistoricalIntelligenceStrength.WEAK


class HistoricalIntelligenceSynthesizer:
    VERSION = HISTORICAL_INTELLIGENCE_VERSION

    @classmethod
    def synthesize_entity(cls, entity_id: str, nodes: list[dict[str, Any]]) -> list[HistoricalIntelligenceSignal]:
        if not nodes:
            return []

        by_group: DefaultDict[str, list[dict[str, Any]]] = defaultdict(list)
        for node in nodes:
            props = node.get("properties", {}) if isinstance(node.get("properties"), dict) else {}
            group = str(props.get("comparison_group") or "unknown")
            by_group[group].append(node)

        signals: list[HistoricalIntelligenceSignal] = []
        for group, group_nodes in sorted(by_group.items()):
            signals.append(cls._trajectory_signal(entity_id, group, group_nodes))
            signals.append(cls._consistency_signal(entity_id, group, group_nodes))
        return signals

    @classmethod
    def _trajectory_signal(cls, entity_id: str, group: str, nodes: list[dict[str, Any]]) -> HistoricalIntelligenceSignal:
        confidences = [float(node.get("confidence", 0.0) or 0.0) for node in nodes]
        confidence = round(_clamp(mean(confidences) if confidences else 0.0), 4)

        aggregate_counts: dict[str, int] = {"improved": 0, "declined": 0, "stable": 0, "unknown": 0}
        momentum_values: list[float] = []
        evidence_signal_ids: list[str] = []
        evidence_node_ids: list[str] = []
        known_gaps: list[str] = []

        for node in nodes:
            props = node.get("properties", {}) if isinstance(node.get("properties"), dict) else {}
            evidence_node_ids.append(str(node.get("id")))
            if props.get("signal_id"):
                evidence_signal_ids.append(str(props.get("signal_id")))
            for key in aggregate_counts:
                aggregate_counts[key] += int((props.get("change_counts", {}) or {}).get(key, 0) or 0)
            try:
                momentum_values.append(float(props.get("momentum_score", 0.0) or 0.0))
            except (TypeError, ValueError):
                pass
            known_gaps.extend([str(gap) for gap in props.get("known_gaps", []) or []])

        fallback = str((nodes[0].get("properties", {}) or {}).get("direction", "unknown"))
        direction = _direction_from_counts(aggregate_counts, fallback)
        strength = _strength_from_confidence_and_count(confidence, len(nodes))
        avg_momentum = round(mean(momentum_values), 4) if momentum_values else 0.0

        explanation = (
            f"{entity_id} has a {direction.value} historical trajectory for {group} "
            f"based on {len(nodes)} historical signal node(s)."
        )

        if direction == HistoricalIntelligenceDirection.UNKNOWN:
            known_gaps.append("Historical trajectory direction remains unresolved.")

        return HistoricalIntelligenceSignal(
            id=f"historical_intelligence:{_safe_id(entity_id)}:{_safe_id(group)}:trajectory",
            entity_id=entity_id,
            pattern_type=HistoricalPatternType.TRAJECTORY,
            direction=direction,
            strength=strength,
            confidence=confidence,
            evidence_node_ids=sorted(set(evidence_node_ids)),
            evidence_signal_ids=sorted(set(evidence_signal_ids)),
            explanation=explanation,
            known_gaps=sorted(set(known_gaps)),
            properties={
                "historical_intelligence_version": cls.VERSION,
                "comparison_group": group,
                "node_count": len(nodes),
                "change_counts": aggregate_counts,
                "average_momentum_score": avg_momentum,
            },
        )

    @classmethod
    def _consistency_signal(cls, entity_id: str, group: str, nodes: list[dict[str, Any]]) -> HistoricalIntelligenceSignal:
        confidences = [float(node.get("confidence", 0.0) or 0.0) for node in nodes]
        confidence = round(_clamp((mean(confidences) if confidences else 0.0) * 0.95), 4)
        evidence_node_ids = [str(node.get("id")) for node in nodes]
        evidence_signal_ids = []
        directions = []
        for node in nodes:
            props = node.get("properties", {}) if isinstance(node.get("properties"), dict) else {}
            if props.get("signal_id"):
                evidence_signal_ids.append(str(props.get("signal_id")))
            directions.append(str(props.get("direction") or "unknown"))

        unique_directions = set(directions)
        if len(unique_directions) == 1 and "unknown" not in unique_directions:
            direction = HistoricalIntelligenceDirection.STABLE
            pattern_type = HistoricalPatternType.CONSISTENCY
        elif len(unique_directions) > 1:
            direction = HistoricalIntelligenceDirection.VOLATILE
            pattern_type = HistoricalPatternType.VOLATILITY
        else:
            direction = HistoricalIntelligenceDirection.UNKNOWN
            pattern_type = HistoricalPatternType.INSUFFICIENT

        strength = _strength_from_confidence_and_count(confidence, len(nodes))
        known_gaps = [] if direction != HistoricalIntelligenceDirection.UNKNOWN else [
            "Historical consistency cannot be determined from unknown-only signal directions."
        ]

        explanation = (
            f"{entity_id} has {direction.value} historical consistency for {group} "
            f"across {len(nodes)} historical signal node(s)."
        )

        return HistoricalIntelligenceSignal(
            id=f"historical_intelligence:{_safe_id(entity_id)}:{_safe_id(group)}:consistency",
            entity_id=entity_id,
            pattern_type=pattern_type,
            direction=direction,
            strength=strength,
            confidence=confidence,
            evidence_node_ids=sorted(set(evidence_node_ids)),
            evidence_signal_ids=sorted(set(evidence_signal_ids)),
            explanation=explanation,
            known_gaps=known_gaps,
            properties={
                "historical_intelligence_version": cls.VERSION,
                "comparison_group": group,
                "node_count": len(nodes),
                "directions": sorted(unique_directions),
            },
        )
