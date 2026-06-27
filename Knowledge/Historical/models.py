"""
Athena Sports Intelligence Platform

Epic 4D.3a

Canonical Historical Snapshot Models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SnapshotType(str, Enum):

    TEMPORAL = "temporal"

    SEASON = "season"

    KNOWLEDGE = "knowledge"

    GRAPH = "graph"


@dataclass(slots=True)
class HistoricalSnapshot:

    id: str

    entity_id: str

    snapshot_type: SnapshotType

    captured_at: str

    source: str

    confidence: float

    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):

        return {

            "id": self.id,

            "entity_id": self.entity_id,

            "snapshot_type": self.snapshot_type.value,

            "captured_at": self.captured_at,

            "source": self.source,

            "confidence": self.confidence,

            "properties": self.properties,

        }


@dataclass(slots=True)
class HistoricalSeries:

    entity_id: str

    snapshots: list[HistoricalSnapshot]

    confidence: float

    def to_dict(self):

        return {

            "entity_id": self.entity_id,

            "confidence": self.confidence,

            "snapshot_count": len(self.snapshots),

            "snapshots": [

                snapshot.to_dict()

                for snapshot in self.snapshots

            ],

        }