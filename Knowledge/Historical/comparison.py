"""
Athena Sports Intelligence Platform

Epic 4D.3b

Historical Comparison Engine

Compares two HistoricalSnapshot objects and produces
canonical HistoricalComparison output.
"""

from __future__ import annotations

from typing import Any

from .comparison_models import (
    HistoricalChange,
    HistoricalComparison,
    HistoricalDelta,
)

from .models import HistoricalSnapshot


NUMERIC_KEYS = {
    "points",
    "goals",
    "assists",
    "games_played",
    "points_per_game",
    "years_remaining",
    "contract_years_remaining",
    "production_rank",
    "production_percentile",
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


def _extract_event_properties(
    snapshot: HistoricalSnapshot,
) -> dict[str, Any]:

    properties = snapshot.properties or {}

    event_properties = properties.get(
        "event_properties",
        {},
    )

    return (
        event_properties
        if isinstance(event_properties, dict)
        else {}
    )


def _compare_value(
    key: str,
    previous: Any,
    current: Any,
) -> HistoricalDelta:

    previous_number = _safe_float(previous)
    current_number = _safe_float(current)

    if (
        key in NUMERIC_KEYS
        and previous_number is not None
        and current_number is not None
    ):
        delta = round(
            current_number - previous_number,
            4,
        )

        changed = delta != 0

        confidence = 0.95

        return HistoricalDelta(
            property_name=key,
            previous_value=previous,
            current_value=current,
            delta=delta,
            changed=changed,
            confidence=confidence,
        )

    changed = previous != current

    return HistoricalDelta(
        property_name=key,
        previous_value=previous,
        current_value=current,
        delta=None,
        changed=changed,
        confidence=0.75,
    )


class HistoricalComparator:

    @classmethod
    def compare(
        cls,
        previous: HistoricalSnapshot,
        current: HistoricalSnapshot,
    ) -> HistoricalComparison:

        known_gaps: list[str] = []

        if previous.entity_id != current.entity_id:
            known_gaps.append(
                "Snapshots do not belong to the same entity."
            )

        previous_props = _extract_event_properties(
            previous
        )

        current_props = _extract_event_properties(
            current
        )

        keys = sorted(
            set(previous_props.keys())
            | set(current_props.keys())
        )

        deltas = [
            _compare_value(
                key,
                previous_props.get(key),
                current_props.get(key),
            )
            for key in keys
        ]

        changed = [
            delta
            for delta in deltas
            if delta.changed
        ]

        change = cls._classify_change(
            deltas
        )

        confidence = cls._confidence(
            previous,
            current,
            deltas,
            known_gaps,
        )

        return HistoricalComparison(
            entity_id=current.entity_id,
            previous_snapshot_id=previous.id,
            current_snapshot_id=current.id,
            change=change,
            confidence=confidence,
            deltas=deltas,
            known_gaps=known_gaps
            + (
                []
                if changed
                else ["No property-level changes detected."]
            ),
        )

    @staticmethod
    def _classify_change(
        deltas: list[HistoricalDelta],
    ) -> HistoricalChange:

        numeric_deltas = [
            delta.delta
            for delta in deltas
            if isinstance(delta.delta, (int, float))
        ]

        if not numeric_deltas:
            return HistoricalChange.UNKNOWN

        total = sum(numeric_deltas)

        if total > 0:
            return HistoricalChange.IMPROVED

        if total < 0:
            return HistoricalChange.DECLINED

        return HistoricalChange.STABLE

    @staticmethod
    def _confidence(
        previous: HistoricalSnapshot,
        current: HistoricalSnapshot,
        deltas: list[HistoricalDelta],
        known_gaps: list[str],
    ) -> float:

        if known_gaps:
            return 0.25

        if not deltas:
            return 0.35

        base = (
            previous.confidence
            + current.confidence
        ) / 2

        changed_count = sum(
            1
            for delta in deltas
            if delta.changed
        )

        coverage = min(
            1.0,
            len(deltas) / 4,
        )

        change_factor = (
            1.0
            if changed_count > 0
            else 0.75
        )

        return round(
            max(
                0.0,
                min(
                    1.0,
                    (base * 0.60)
                    + (coverage * 0.25)
                    + (change_factor * 0.15),
                ),
            ),
            4,
        )
