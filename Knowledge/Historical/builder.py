"""
Athena Sports Intelligence Platform

Epic 4D.3a

Historical Snapshot Builder

Builds canonical HistoricalSnapshot objects from existing
temporal evidence.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, DefaultDict

from Knowledge.Graph.temporal_intelligence import (
    build_temporal_evidence,
)

from .models import (
    HistoricalSeries,
    HistoricalSnapshot,
    SnapshotType,
)


def _utc_now() -> str:

    return datetime.now(timezone.utc).isoformat()


def _snapshot_id(
    entity_id: str,
    event_id: str,
) -> str:

    safe = f"{entity_id}:{event_id}".replace(":", "_").replace("/", "_")

    return f"historical_snapshot:{safe}"


def snapshot_from_temporal_event(
    event: dict[str, Any],
) -> HistoricalSnapshot | None:

    entity_id = event.get("subject_id")

    if not entity_id:
        return None

    event_id = event.get("id") or entity_id

    captured_at = (
        event.get("occurred_at")
        or event.get("generated_at")
        or _utc_now()
    )

    return HistoricalSnapshot(
        id=_snapshot_id(
            str(entity_id),
            str(event_id),
        ),
        entity_id=str(entity_id),
        snapshot_type=SnapshotType.TEMPORAL,
        captured_at=str(captured_at),
        source=str(event.get("source") or "temporal_evidence"),
        confidence=float(event.get("confidence", 0.75) or 0.75),
        properties={
            "event_id": event.get("id"),
            "event_type": event.get("type"),
            "event_label": event.get("label"),
            "event_properties": event.get("properties", {}),
        },
    )


def build_historical_snapshots(
    project_root: Path | None = None,
) -> list[HistoricalSnapshot]:

    temporal = build_temporal_evidence(project_root)

    timeline = temporal.get("timeline", {})

    events = timeline.get("events", [])

    snapshots: list[HistoricalSnapshot] = []

    for event in events:

        if not isinstance(event, dict):
            continue

        snapshot = snapshot_from_temporal_event(event)

        if snapshot is not None:
            snapshots.append(snapshot)

    return snapshots


def build_historical_series(
    snapshots: list[HistoricalSnapshot],
) -> list[HistoricalSeries]:

    grouped: DefaultDict[str, list[HistoricalSnapshot]] = defaultdict(list)

    for snapshot in snapshots:
        grouped[snapshot.entity_id].append(snapshot)

    series: list[HistoricalSeries] = []

    for entity_id, items in sorted(grouped.items()):

        items = sorted(
            items,
            key=lambda item: (
                item.captured_at,
                item.id,
            ),
        )

        confidence = (
            mean([item.confidence for item in items])
            if items
            else 0.0
        )

        series.append(
            HistoricalSeries(
                entity_id=entity_id,
                snapshots=items,
                confidence=round(confidence, 4),
            )
        )

    return series