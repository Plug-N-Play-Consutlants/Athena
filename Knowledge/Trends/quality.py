"""
Athena Sports Intelligence Platform

Epic 4D.2d

Trend data quality analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import pstdev
from typing import Any

from Knowledge.Trends.models import TrendSeries


@dataclass(frozen=True)
class TrendQualityReport:
    observation_count: int
    missing_count: int
    completeness_score: float
    freshness_score: float
    consistency_score: float
    quality_score: float
    known_gaps: list[str]

    def serialize(self) -> dict:
        return {
            "observation_count": self.observation_count,
            "missing_count": self.missing_count,
            "completeness_score": self.completeness_score,
            "freshness_score": self.freshness_score,
            "consistency_score": self.consistency_score,
            "quality_score": self.quality_score,
            "known_gaps": list(self.known_gaps),
        }


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 4)


class TrendQualityAnalyzer:
    @classmethod
    def analyze(cls, series: TrendSeries) -> TrendQualityReport:
        observations = list(series.observations or [])
        observation_count = len(observations)
        missing_count = int(getattr(series.window, "missing_count", 0) or 0)
        total = observation_count + missing_count
        completeness_score = observation_count / total if total else 0.0
        freshness_score = cls._freshness_score(observations)
        consistency_score = cls._consistency_score(observations)
        quality_score = _clamp(
            completeness_score * 0.45
            + freshness_score * 0.25
            + consistency_score * 0.30
        )
        known_gaps: list[str] = []
        if observation_count < 2:
            known_gaps.append("Fewer than two observations are available.")
        if missing_count > 0:
            known_gaps.append(f"{missing_count} missing observation(s) were detected.")
        if freshness_score < 0.5:
            known_gaps.append("The most recent observation is stale.")
        return TrendQualityReport(
            observation_count=observation_count,
            missing_count=missing_count,
            completeness_score=_clamp(completeness_score),
            freshness_score=_clamp(freshness_score),
            consistency_score=_clamp(consistency_score),
            quality_score=quality_score,
            known_gaps=known_gaps,
        )

    @staticmethod
    def _freshness_score(observations: list[Any]) -> float:
        if not observations:
            return 0.0
        dates = [_parse_datetime(getattr(obs, "observed_at", None)) for obs in observations]
        dates = [dt for dt in dates if dt is not None]
        if not dates:
            return 0.0
        age_days = max(0, (datetime.now(timezone.utc) - max(dates)).days)
        if age_days <= 7:
            return 1.0
        if age_days <= 30:
            return 0.85
        if age_days <= 90:
            return 0.65
        if age_days <= 180:
            return 0.40
        return 0.20

    @staticmethod
    def _consistency_score(observations: list[Any]) -> float:
        values: list[float] = []
        for obs in observations:
            value = getattr(obs, "value", None)
            if isinstance(value, bool):
                values.append(1.0 if value else 0.0)
            elif isinstance(value, (int, float)):
                values.append(float(value))
        if len(values) < 2:
            return 0.5
        average = sum(values) / len(values)
        if average == 0:
            return 0.5
        coefficient = pstdev(values) / abs(average)
        return _clamp(1.0 - min(coefficient, 1.0))
