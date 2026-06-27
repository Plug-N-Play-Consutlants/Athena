"""
Athena Sports Intelligence Platform

Epic 4D.3d

Historical Trend Synthesizer

Turns grouped historical comparisons into higher-level historical trend signals.
"""

from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Any, DefaultDict

from .synthesis_models import (
    HistoricalSignalDirection,
    HistoricalSignalStrength,
    HistoricalTrendSignal,
)


CHANGE_SCORES = {
    "improved": 1.0,
    "declined": -1.0,
    "stable": 0.0,
    "unknown": 0.0,
}


def _safe_float(value: Any) -> float | None:

    if value in (None, "", [], {}):
        return None

    if isinstance(value, bool):
        return 1.0 if value else 0.0

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _signal_id(entity_id: str, comparison_group: str) -> str:

    safe = f"{entity_id}:{comparison_group}".replace(":", "_").replace("/", "_")

    return f"historical_trend_signal:{safe}"


class HistoricalTrendSynthesizer:

    @classmethod
    def synthesize(
        cls,
        comparisons: list[dict[str, Any]],
    ) -> list[HistoricalTrendSignal]:

        grouped: DefaultDict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

        for comparison in comparisons:

            if not isinstance(comparison, dict):
                continue

            entity_id = str(comparison.get("entity_id") or "")

            if not entity_id:
                continue

            comparison_group = str(
                comparison.get("comparison_group")
                or comparison.get("properties", {}).get("comparison_group")
                or "unknown"
            )

            grouped[(entity_id, comparison_group)].append(comparison)

        signals: list[HistoricalTrendSignal] = []

        for (entity_id, comparison_group), items in sorted(grouped.items()):

            signals.append(
                cls.synthesize_group(
                    entity_id=entity_id,
                    comparison_group=comparison_group,
                    comparisons=items,
                )
            )

        return signals

    @classmethod
    def synthesize_group(
        cls,
        *,
        entity_id: str,
        comparison_group: str,
        comparisons: list[dict[str, Any]],
    ) -> HistoricalTrendSignal:

        ordered = sorted(
            comparisons,
            key=lambda item: (
                item.get("previous_snapshot_id") or "",
                item.get("current_snapshot_id") or "",
            ),
        )

        change_counts: dict[str, int] = {
            "improved": 0,
            "declined": 0,
            "stable": 0,
            "unknown": 0,
        }

        scores: list[float] = []

        confidences: list[float] = []

        comparison_ids: list[str] = []

        numeric_delta_values: DefaultDict[str, list[float]] = defaultdict(list)

        known_gaps: list[str] = []

        for comparison in ordered:

            change = str(comparison.get("change") or "unknown")

            if change not in change_counts:
                change = "unknown"

            change_counts[change] += 1

            scores.append(CHANGE_SCORES[change])

            confidence = _safe_float(comparison.get("confidence"))

            if confidence is not None:
                confidences.append(confidence)

            comparison_ids.append(
                cls._comparison_evidence_id(comparison)
            )

            for delta in comparison.get("deltas", []) or []:

                if not isinstance(delta, dict):
                    continue

                delta_value = _safe_float(delta.get("delta"))

                if delta_value is None:
                    continue

                numeric_delta_values[
                    str(delta.get("property_name") or "unknown")
                ].append(delta_value)

            for gap in comparison.get("known_gaps", []) or []:
                if gap not in known_gaps:
                    known_gaps.append(str(gap))

        comparison_count = len(ordered)

        momentum_score = round(
            sum(scores) / comparison_count,
            4,
        ) if comparison_count else 0.0

        direction = cls._direction(
            change_counts,
            momentum_score,
            comparison_count,
        )

        strength = cls._strength(
            momentum_score,
            comparison_count,
        )

        confidence = cls._confidence(
            confidences,
            comparison_count,
            direction,
        )

        if comparison_count < 2:
            known_gaps.append(
                "Only one comparable historical comparison is available."
            )

        if change_counts.get("unknown", 0) == comparison_count:
            known_gaps.append(
                "All comparable historical comparisons are classified as unknown."
            )

        delta_summary = {
            key: {
                "count": len(values),
                "average_delta": round(mean(values), 4),
                "total_delta": round(sum(values), 4),
            }
            for key, values in sorted(numeric_delta_values.items())
            if values
        }

        return HistoricalTrendSignal(
            id=_signal_id(entity_id, comparison_group),
            entity_id=entity_id,
            comparison_group=comparison_group,
            direction=direction,
            strength=strength,
            momentum_score=momentum_score,
            confidence=confidence,
            comparison_count=comparison_count,
            change_counts=change_counts,
            evidence_comparison_ids=comparison_ids,
            delta_summary=delta_summary,
            known_gaps=known_gaps,
            properties={
                "synthesis_version": "4D.3d-historical-trend-synthesis",
            },
        )

    @staticmethod
    def _comparison_evidence_id(
        comparison: dict[str, Any],
    ) -> str:

        previous_id = str(comparison.get("previous_snapshot_id") or "previous")

        current_id = str(comparison.get("current_snapshot_id") or "current")

        safe = f"{previous_id}:{current_id}".replace(":", "_").replace("/", "_")

        return f"historical_comparison:{safe}"

    @staticmethod
    def _direction(
        change_counts: dict[str, int],
        momentum_score: float,
        comparison_count: int,
    ) -> HistoricalSignalDirection:

        if comparison_count <= 0:
            return HistoricalSignalDirection.UNKNOWN

        if change_counts.get("unknown", 0) == comparison_count:
            return HistoricalSignalDirection.UNKNOWN

        if abs(momentum_score) < 0.10:
            if change_counts.get("improved", 0) and change_counts.get("declined", 0):
                return HistoricalSignalDirection.MIXED
            return HistoricalSignalDirection.STABLE

        if momentum_score > 0:
            return HistoricalSignalDirection.IMPROVING

        return HistoricalSignalDirection.DECLINING

    @staticmethod
    def _strength(
        momentum_score: float,
        comparison_count: int,
    ) -> HistoricalSignalStrength:

        if comparison_count <= 0:
            return HistoricalSignalStrength.NONE

        magnitude = abs(momentum_score)

        if magnitude < 0.10:
            return HistoricalSignalStrength.NONE

        if magnitude < 0.35:
            return HistoricalSignalStrength.WEAK

        if magnitude < 0.70:
            return HistoricalSignalStrength.MODERATE

        return HistoricalSignalStrength.STRONG

    @staticmethod
    def _confidence(
        confidences: list[float],
        comparison_count: int,
        direction: HistoricalSignalDirection,
    ) -> float:

        if comparison_count <= 0:
            return 0.0

        base = mean(confidences) if confidences else 0.50

        coverage = min(1.0, comparison_count / 3.0)

        direction_factor = 0.60 if direction == HistoricalSignalDirection.UNKNOWN else 1.0

        return round(
            max(
                0.0,
                min(
                    1.0,
                    (base * 0.65) + (coverage * 0.25) + (direction_factor * 0.10),
                ),
            ),
            4,
        )
