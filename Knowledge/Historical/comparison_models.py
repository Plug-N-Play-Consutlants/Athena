"""
Athena Sports Intelligence Platform

Epic 4D.3b / 4D.3c

Historical Comparison Models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HistoricalChange(str, Enum):

    IMPROVED = "improved"

    DECLINED = "declined"

    STABLE = "stable"

    UNKNOWN = "unknown"


@dataclass(slots=True)
class HistoricalDelta:

    property_name: str

    previous_value: Any

    current_value: Any

    delta: Any

    changed: bool

    confidence: float

    def to_dict(self):

        return {
            "property_name": self.property_name,
            "previous_value": self.previous_value,
            "current_value": self.current_value,
            "delta": self.delta,
            "changed": self.changed,
            "confidence": self.confidence,
        }


@dataclass(slots=True)
class HistoricalComparison:

    entity_id: str

    previous_snapshot_id: str

    current_snapshot_id: str

    change: HistoricalChange

    confidence: float

    deltas: list[HistoricalDelta] = field(default_factory=list)

    known_gaps: list[str] = field(default_factory=list)

    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):

        payload = {

            "entity_id": self.entity_id,

            "previous_snapshot_id": self.previous_snapshot_id,

            "current_snapshot_id": self.current_snapshot_id,

            "change": self.change.value,

            "confidence": self.confidence,

            "delta_count": len(self.deltas),

            "deltas": [
                delta.to_dict()
                for delta in self.deltas
            ],

            "known_gaps": self.known_gaps,
        }

        if self.properties:
            payload["properties"] = self.properties

        return payload