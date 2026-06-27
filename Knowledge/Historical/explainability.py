"""
Athena Sports Intelligence Platform

Epic 4D.3e

Historical Signal Explainability
"""

from __future__ import annotations

from typing import Any

from .confidence import HistoricalConfidencePackage
from .explainability_models import (
    HistoricalExplanationPoint,
    HistoricalExplanationSeverity,
    HistoricalSignalExplanation,
)


HISTORICAL_EXPLAINABILITY_VERSION = "4D.3e-historical-signal-explainability"


class HistoricalSignalExplanationBuilder:
    """Builds human- and Scout-readable explanations for historical signals."""

    @classmethod
    def build(
        cls,
        signal: dict[str, Any],
        confidence: HistoricalConfidencePackage,
    ) -> HistoricalSignalExplanation:
        signal_id = str(signal.get("id") or "")
        entity_id = str(signal.get("entity_id") or "")
        comparison_group = str(signal.get("comparison_group") or "unknown")
        direction = str(signal.get("direction") or "unknown")
        strength = str(signal.get("strength") or "none")
        comparison_count = int(signal.get("comparison_count") or 0)
        momentum = float(signal.get("momentum_score") or 0.0)

        summary = (
            f"{entity_id} has a {direction} historical signal "
            f"for {comparison_group} with {strength} strength."
        )

        evidence = [
            HistoricalExplanationPoint(
                label="Comparison group",
                detail=f"Signal is synthesized from the {comparison_group} comparison group.",
                properties={"comparison_group": comparison_group},
            ),
            HistoricalExplanationPoint(
                label="Comparison count",
                detail=f"Signal is based on {comparison_count} comparable historical comparison(s).",
                properties={"comparison_count": comparison_count},
            ),
            HistoricalExplanationPoint(
                label="Momentum",
                detail=f"Historical momentum score is {momentum:.4f}.",
                properties={"momentum_score": momentum},
            ),
        ]

        change_counts = signal.get("change_counts") or {}
        if isinstance(change_counts, dict):
            evidence.append(
                HistoricalExplanationPoint(
                    label="Change counts",
                    detail=f"Change distribution is {change_counts}.",
                    properties={"change_counts": change_counts},
                )
            )

        limitations: list[HistoricalExplanationPoint] = []
        for gap in signal.get("known_gaps") or []:
            limitations.append(
                HistoricalExplanationPoint(
                    label="Known limitation",
                    detail=str(gap),
                    severity=HistoricalExplanationSeverity.LIMITATION,
                )
            )

        if direction == "unknown":
            limitations.append(
                HistoricalExplanationPoint(
                    label="Direction unresolved",
                    detail="Historical comparisons did not produce a clear improved, declined, or stable direction.",
                    severity=HistoricalExplanationSeverity.WARNING,
                )
            )

        confidence_notes = [
            HistoricalExplanationPoint(
                label="Confidence",
                detail=f"Historical explainability confidence is {confidence.band.value} ({confidence.score:.4f}).",
                properties=confidence.to_dict(),
            )
        ]

        return HistoricalSignalExplanation(
            signal_id=signal_id,
            entity_id=entity_id,
            comparison_group=comparison_group,
            summary=summary,
            evidence=evidence,
            limitations=limitations,
            confidence_notes=confidence_notes,
            properties={"historical_explainability_version": HISTORICAL_EXPLAINABILITY_VERSION},
        )


def metadata() -> dict[str, str]:
    return {"historical_explainability_version": HISTORICAL_EXPLAINABILITY_VERSION}
