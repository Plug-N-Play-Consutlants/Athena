"""
Athena Sports Intelligence Platform

Epic 4D.2d

Trend confidence calculation.
"""

from __future__ import annotations

from Knowledge.Trends.confidence_models import (
    ConfidenceBand,
    ConfidenceComponent,
    ConfidenceFactor,
    ConfidencePackage,
)
from Knowledge.Trends.models import TrendResult, TrendSeries
from Knowledge.Trends.quality import TrendQualityAnalyzer


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 4)


def confidence_band(score: float) -> ConfidenceBand:
    score = _clamp(score)
    if score < 0.20:
        return ConfidenceBand.INSUFFICIENT
    if score < 0.40:
        return ConfidenceBand.LOW
    if score < 0.70:
        return ConfidenceBand.MEDIUM
    if score < 0.90:
        return ConfidenceBand.HIGH
    return ConfidenceBand.VERY_HIGH


class TrendConfidenceCalculator:
    @classmethod
    def calculate(cls, series: TrendSeries, result: TrendResult) -> ConfidencePackage:
        quality = TrendQualityAnalyzer.analyze(series)
        stability = cls._stability_score(result)
        components = [
            ConfidenceComponent(
                factor=ConfidenceFactor.OBSERVATION_COUNT,
                score=cls._observation_count_score(series),
                weight=0.25,
                explanation=f"{len(series.observations)} observation(s) available.",
            ),
            ConfidenceComponent(
                factor=ConfidenceFactor.DATA_COMPLETENESS,
                score=quality.completeness_score,
                weight=0.20,
                explanation=f"Completeness score is {quality.completeness_score:.2f}.",
            ),
            ConfidenceComponent(
                factor=ConfidenceFactor.DATA_FRESHNESS,
                score=quality.freshness_score,
                weight=0.15,
                explanation=f"Freshness score is {quality.freshness_score:.2f}.",
            ),
            ConfidenceComponent(
                factor=ConfidenceFactor.METRIC_QUALITY,
                score=quality.quality_score,
                weight=0.20,
                explanation=f"Overall quality score is {quality.quality_score:.2f}.",
            ),
            ConfidenceComponent(
                factor=ConfidenceFactor.TREND_STABILITY,
                score=stability,
                weight=0.20,
                explanation=f"Trend stability score is {stability:.2f}.",
            ),
        ]
        total_weight = sum(component.weight for component in components)
        overall = _clamp(sum(component.score * component.weight for component in components) / total_weight) if total_weight else 0.0
        known_gaps = _dedupe(list(quality.known_gaps) + list(result.known_gaps or []))
        return ConfidencePackage(
            overall_score=overall,
            confidence_band=confidence_band(overall),
            components=components,
            known_gaps=known_gaps,
            recommendations=cls._recommendations(overall, series, result),
        )

    @staticmethod
    def _observation_count_score(series: TrendSeries) -> float:
        count = len(series.observations or [])
        if count <= 0:
            return 0.0
        if count == 1:
            return 0.25
        if count == 2:
            return 0.45
        if count <= 5:
            return 0.65
        if count <= 10:
            return 0.80
        return 1.0

    @staticmethod
    def _stability_score(result: TrendResult) -> float:
        momentum = abs(float(result.momentum_score or 0.0))
        if momentum <= 0.05:
            return 0.75
        if momentum <= 0.20:
            return 0.85
        if momentum <= 0.50:
            return 0.70
        return 0.55

    @staticmethod
    def _recommendations(score: float, series: TrendSeries, result: TrendResult) -> list[str]:
        recommendations: list[str] = []
        if len(series.observations or []) < 2:
            recommendations.append("Collect additional observations before treating this as directional.")
        if score < 0.40:
            recommendations.append("Use this trend as weak context only.")
        if abs(float(result.momentum_score or 0.0)) > 0.50:
            recommendations.append("Review the underlying window comparisons before relying on the momentum score.")
        return recommendations


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            output.append(item)
    return output
