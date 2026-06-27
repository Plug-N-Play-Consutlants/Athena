"""
Athena Sports Intelligence Platform

Epic 4D.3d

Historical Trend Synthesis Models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HistoricalSignalDirection(str, Enum):

    IMPROVING = "improving"

    DECLINING = "declining"

    STABLE = "stable"

    MIXED = "mixed"

    UNKNOWN = "unknown"


class HistoricalSignalStrength(str, Enum):

    NONE = "none"

    WEAK = "weak"

    MODERATE = "moderate"

    STRONG = "strong"


@dataclass(slots=True)
class HistoricalTrendSignal:

    id: str

    entity_id: str

    comparison_group: str

    direction: HistoricalSignalDirection

    strength: HistoricalSignalStrength

    momentum_score: float

    confidence: float

    comparison_count: int

    change_counts: dict[str, int] = field(default_factory=dict)

    evidence_comparison_ids: list[str] = field(default_factory=list)

    delta_summary: dict[str, Any] = field(default_factory=dict)

    known_gaps: list[str] = field(default_factory=list)

    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:

        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "comparison_group": self.comparison_group,
            "direction": self.direction.value,
            "strength": self.strength.value,
            "momentum_score": self.momentum_score,
            "confidence": self.confidence,
            "comparison_count": self.comparison_count,
            "change_counts": self.change_counts,
            "evidence_comparison_ids": self.evidence_comparison_ids,
            "delta_summary": self.delta_summary,
            "known_gaps": self.known_gaps,
            "properties": self.properties,
        }
