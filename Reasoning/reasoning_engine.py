"""Athena Reasoning Engine."""
from __future__ import annotations

from typing import Any

try:
    from Reasoning.primitives.asset_assessor import AssetAssessor
except Exception:  # pragma: no cover
    AssetAssessor = None  # type: ignore

from Reasoning.primitives.player_assessor import PlayerAssessor


class ReasoningEngine:
    """Deterministic orchestrator for reasoning primitives."""

    def __init__(self, collector: Any = None, registry: Any = None):
        self.collector = collector
        self.registry = registry
        self.asset_assessor = AssetAssessor() if AssetAssessor is not None else None
        self.player_assessor = PlayerAssessor()

    def reason_about_asset(self, *evidence_sets: Any) -> dict:
        if self.asset_assessor is not None:
            return self.asset_assessor.assess(*evidence_sets)
        return {"summary": "Generic asset assessor is not installed.", "key_findings": [], "overall_confidence": 0.0}

    def reason_about_player(self, profile: Any = None, evidence_bundle: Any = None) -> Any:
        return self.player_assessor.assess(profile, evidence_bundle)

    def reason(self, request: Any) -> Any:
        reasoning_type = getattr(request, "reasoning_type", None) or "assessment"

        if reasoning_type == "player_assessment":
            return self.reason_about_player(
                getattr(request, "subject", None),
                getattr(request, "evidence_bundle", None),
            )

        if reasoning_type in {"assessment", "asset_assessment", "asset"}:
            evidence = getattr(request, "evidence_bundle", None)
            if evidence is None and self.collector is not None:
                evidence = self.collector.collect(request)
            return self.reason_about_asset(evidence or [])

        raise NotImplementedError(f"Unsupported reasoning type: {reasoning_type}")
