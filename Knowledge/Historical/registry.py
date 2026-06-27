"""
Athena Sports Intelligence Platform

Epic 4D.3a

Historical Registry
"""

from __future__ import annotations

from collections import defaultdict
from typing import DefaultDict

from .models import (
    HistoricalSeries,
    HistoricalSnapshot,
)


class HistoricalRegistry:

    def __init__(self):

        self._snapshots: dict[str, HistoricalSnapshot] = {}

        self._entity_index: DefaultDict[
            str,
            list[str],
        ] = defaultdict(list)

    def clear(self):

        self._snapshots.clear()

        self._entity_index.clear()

    def register_snapshot(
        self,
        snapshot: HistoricalSnapshot,
    ):

        self._snapshots[snapshot.id] = snapshot

        self._entity_index[
            snapshot.entity_id
        ].append(snapshot.id)

    def register_snapshots(
        self,
        snapshots: list[HistoricalSnapshot],
    ):

        for snapshot in snapshots:
            self.register_snapshot(snapshot)

    def snapshot(
        self,
        snapshot_id: str,
    ) -> HistoricalSnapshot | None:

        return self._snapshots.get(snapshot_id)

    def snapshots_for_entity(
        self,
        entity_id: str,
    ) -> list[HistoricalSnapshot]:

        ids = self._entity_index.get(
            entity_id,
            [],
        )

        snapshots = [
            self._snapshots[i]
            for i in ids
            if i in self._snapshots
        ]

        return sorted(
            snapshots,
            key=lambda s: (
                s.captured_at,
                s.id,
            ),
        )

    def build_series(
        self,
        entity_id: str,
    ) -> HistoricalSeries | None:

        snapshots = self.snapshots_for_entity(
            entity_id
        )

        if not snapshots:
            return None

        confidence = round(
            sum(
                s.confidence
                for s in snapshots
            ) / len(snapshots),
            4,
        )

        return HistoricalSeries(
            entity_id=entity_id,
            snapshots=snapshots,
            confidence=confidence,
        )

    def entities(self) -> list[str]:

        return sorted(
            self._entity_index.keys()
        )

    def snapshot_count(self) -> int:

        return len(
            self._snapshots
        )

    def entity_count(self) -> int:

        return len(
            self._entity_index
        )


_registry = HistoricalRegistry()


def get_historical_registry() -> HistoricalRegistry:

    return _registry