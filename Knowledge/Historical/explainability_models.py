"""
Athena Sports Intelligence Platform

Epic 4D.3e

Historical Signal Explainability Models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HistoricalExplanationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    LIMITATION = "limitation"


@dataclass(slots=True)
class HistoricalExplanationPoint:
    label: str
    detail: str
    severity: HistoricalExplanationSeverity = HistoricalExplanationSeverity.INFO
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "detail": self.detail,
            "severity": self.severity.value,
            "properties": self.properties,
        }


@dataclass(slots=True)
class HistoricalSignalExplanation:
    signal_id: str
    entity_id: str
    comparison_group: str
    summary: str
    evidence: list[HistoricalExplanationPoint] = field(default_factory=list)
    limitations: list[HistoricalExplanationPoint] = field(default_factory=list)
    confidence_notes: list[HistoricalExplanationPoint] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "entity_id": self.entity_id,
            "comparison_group": self.comparison_group,
            "summary": self.summary,
            "evidence": [point.to_dict() for point in self.evidence],
            "limitations": [point.to_dict() for point in self.limitations],
            "confidence_notes": [point.to_dict() for point in self.confidence_notes],
            "properties": self.properties,
        }
