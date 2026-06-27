"""
Athena Sports Intelligence Platform

Epic 4D.4

Historical Intelligence Models

Converts historical graph-ready signals into higher-order historical
intelligence patterns such as trajectory, consistency, volatility, and
regression risk.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HistoricalPatternType(str, Enum):
    TRAJECTORY = "trajectory"
    CONSISTENCY = "consistency"
    VOLATILITY = "volatility"
    REGRESSION = "regression"
    INSUFFICIENT = "insufficient"


class HistoricalIntelligenceDirection(str, Enum):
    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"


class HistoricalIntelligenceStrength(str, Enum):
    NONE = "none"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


@dataclass(slots=True)
class HistoricalIntelligenceSignal:
    id: str
    entity_id: str
    pattern_type: HistoricalPatternType
    direction: HistoricalIntelligenceDirection
    strength: HistoricalIntelligenceStrength
    confidence: float
    evidence_node_ids: list[str] = field(default_factory=list)
    evidence_signal_ids: list[str] = field(default_factory=list)
    explanation: str = ""
    known_gaps: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "pattern_type": self.pattern_type.value,
            "direction": self.direction.value,
            "strength": self.strength.value,
            "confidence": self.confidence,
            "evidence_node_ids": self.evidence_node_ids,
            "evidence_signal_ids": self.evidence_signal_ids,
            "explanation": self.explanation,
            "known_gaps": self.known_gaps,
            "properties": self.properties,
        }
