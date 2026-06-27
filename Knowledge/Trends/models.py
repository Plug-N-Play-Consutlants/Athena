"""Canonical trend domain models for Athena.

Drop 4D.2a establishes the domain language only. Analytical computation is
implemented in later drops, but these dataclasses are intentionally complete
enough for deterministic serialization, validation, registry use, and future
graph integration.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from Knowledge.Trends.enums import (
    TrendConfidenceBand,
    TrendDirection,
    TrendStrength,
    TrendType,
    TrendValueKind,
    TrendWindowType,
)
from Knowledge.Trends.version import TREND_DOMAIN_VERSION, TREND_SCHEMA_VERSION


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clamp_confidence(value: float | int | None) -> float:
    """Normalize confidence to Athena's canonical 0.0-1.0 range."""

    try:
        number = float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        number = 0.0
    return round(max(0.0, min(1.0, number)), 4)


def confidence_band(confidence: float | int | None) -> TrendConfidenceBand:
    """Map numeric confidence to a stable confidence band."""

    score = clamp_confidence(confidence)
    if score >= 0.8:
        return TrendConfidenceBand.HIGH
    if score >= 0.55:
        return TrendConfidenceBand.MEDIUM
    if score > 0.0:
        return TrendConfidenceBand.LOW
    return TrendConfidenceBand.INSUFFICIENT


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def _serialize_dict(payload: Dict[str, Any]) -> Dict[str, Any]:
    serialized: Dict[str, Any] = {}
    for key, value in payload.items():
        if hasattr(value, "value"):
            serialized[key] = value.value
        elif isinstance(value, list):
            serialized[key] = [_serialize_dict(item) if isinstance(item, dict) else _enum_value(item) for item in value]
        elif isinstance(value, dict):
            serialized[key] = _serialize_dict(value)
        else:
            serialized[key] = value
    return serialized


@dataclass(frozen=True)
class TrendMetric:
    """A canonical measurable signal that may produce trends later."""

    key: str
    label: str
    trend_type: TrendType = TrendType.GENERIC
    value_kind: TrendValueKind = TrendValueKind.NUMERIC
    unit: str = ""
    higher_is_better: Optional[bool] = None
    description: str = ""
    source_event_types: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _serialize_dict(asdict(self))


@dataclass(frozen=True)
class TrendWindow:
    """A time window over which a trend can be interpreted."""

    window_type: TrendWindowType = TrendWindowType.CUSTOM
    label: str = "custom"
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    observation_count: int = 0
    missing_count: int = 0
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _serialize_dict(asdict(self))


@dataclass(frozen=True)
class TrendObservation:
    """One canonical observation used by future trend calculations."""

    id: str
    entity_id: str
    metric_key: str
    value: Any
    observed_at: Optional[str] = None
    source_event_id: Optional[str] = None
    confidence: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", clamp_confidence(self.confidence))

    def to_dict(self) -> Dict[str, Any]:
        return _serialize_dict(asdict(self))


@dataclass(frozen=True)
class TrendSeries:
    """A collection of observations for one entity and metric."""

    id: str
    entity_id: str
    metric: TrendMetric
    observations: List[TrendObservation] = field(default_factory=list)
    window: Optional[TrendWindow] = None
    confidence: float = 0.0
    source_event_ids: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", clamp_confidence(self.confidence))

    @property
    def observation_count(self) -> int:
        return len(self.observations)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["observation_count"] = self.observation_count
        return _serialize_dict(payload)


@dataclass(frozen=True)
class TrendResult:
    """Canonical output of a future trend calculation."""

    id: str
    entity_id: str
    trend_type: TrendType
    metric_key: str
    direction: TrendDirection = TrendDirection.UNKNOWN
    strength: TrendStrength = TrendStrength.UNKNOWN
    confidence: float = 0.0
    confidence_band: TrendConfidenceBand = TrendConfidenceBand.UNKNOWN
    momentum_score: float = 0.0
    window: Optional[TrendWindow] = None
    observation_count: int = 0
    evidence_event_ids: List[str] = field(default_factory=list)
    explanation: str = ""
    known_gaps: List[str] = field(default_factory=list)
    generated_at: str = field(default_factory=_utc_now)
    trend_domain_version: str = TREND_DOMAIN_VERSION
    trend_schema_version: str = TREND_SCHEMA_VERSION
    properties: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized = clamp_confidence(self.confidence)
        object.__setattr__(self, "confidence", normalized)
        if self.confidence_band == TrendConfidenceBand.UNKNOWN:
            object.__setattr__(self, "confidence_band", confidence_band(normalized))
        object.__setattr__(self, "momentum_score", round(max(-1.0, min(1.0, float(self.momentum_score))), 4))

    def to_dict(self) -> Dict[str, Any]:
        return _serialize_dict(asdict(self))


@dataclass(frozen=True)
class Trend:
    """Graph-ready trend entity wrapper."""

    id: str
    entity_id: str
    trend_type: TrendType
    label: str
    result: TrendResult
    source_series_ids: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _serialize_dict(asdict(self))


def serialize_trends(items: Iterable[Any]) -> List[Dict[str, Any]]:
    """Serialize any trend-domain objects that expose to_dict()."""

    output: List[Dict[str, Any]] = []
    for item in items:
        if hasattr(item, "to_dict"):
            output.append(item.to_dict())
        elif isinstance(item, dict):
            output.append(_serialize_dict(item))
        else:
            output.append({"value": str(item)})
    return output
