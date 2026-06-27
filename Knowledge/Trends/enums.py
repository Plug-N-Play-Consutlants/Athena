"""Canonical trend enumerations for Athena Trend Intelligence.

This module intentionally contains no sport-specific concepts. Trend Intelligence
must remain a generic analytical layer over temporal evidence.
"""

from __future__ import annotations

from enum import Enum


class SerializableEnum(str, Enum):
    """String enum with stable serialization helpers."""

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


class TrendDirection(SerializableEnum):
    RISING = "rising"
    STABLE = "stable"
    DECLINING = "declining"
    VOLATILE = "volatile"
    INSUFFICIENT_DATA = "insufficient_data"
    UNKNOWN = "unknown"


class TrendStrength(SerializableEnum):
    NONE = "none"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    EXTREME = "extreme"
    UNKNOWN = "unknown"


class TrendType(SerializableEnum):
    PERFORMANCE = "performance"
    USAGE = "usage"
    AVAILABILITY = "availability"
    ROLE = "role"
    ORGANIZATIONAL = "organizational"
    CONTRACT = "contract"
    KNOWLEDGE = "knowledge"
    GENERIC = "generic"


class TrendWindowType(SerializableEnum):
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"
    CUSTOM = "custom"
    ALL_TIME = "all_time"


class TrendConfidenceBand(SerializableEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT = "insufficient"
    UNKNOWN = "unknown"


class TrendValueKind(SerializableEnum):
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"
    TEXT = "text"
    MIXED = "mixed"
