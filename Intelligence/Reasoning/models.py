"""Canonical models for Athena cross-sport reasoning."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Tuple

CROSS_SPORT_REASONING_VERSION = "0.5.5.3.0"


@dataclass(frozen=True)
class ReasoningAdapter:
    """Sport-specific reasoning adapter contract.

    The adapter is intentionally light. It describes how to frame terminology and
    evidence for a sport while leaving orchestration to the cross-sport engine.
    """

    sport: str
    leagues: Tuple[str, ...]
    label: str
    terminology: Dict[str, str] = field(default_factory=dict)
    supported_intents: Tuple[str, ...] = ("general", "profile", "summary", "comparison", "event_context")
    evidence_preferences: Tuple[str, ...] = ("identity", "knowledge", "events", "historical")
    status: str = "active"

    def supports(self, sport: str = "", league: str = "", intent: str = "general") -> bool:
        sport_key = str(sport or "").strip().lower()
        league_key = str(league or "").strip().upper()
        intent_key = str(intent or "general").strip().lower()
        sport_ok = not sport_key or sport_key == self.sport.lower()
        league_ok = not league_key or league_key in {item.upper() for item in self.leagues}
        intent_ok = intent_key in self.supported_intents or "general" in self.supported_intents
        return sport_ok and league_ok and intent_ok

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FusedEvidence:
    source: str
    label: str
    detail: str = ""
    confidence: float = 0.5
    weight: float = 1.0
    category: str = "general"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def weighted_confidence(self) -> float:
        return max(0.0, min(1.0, float(self.confidence))) * max(0.0, float(self.weight))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AmbiguityCandidate:
    entity_id: str
    label: str
    sport: str = ""
    league: str = ""
    confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AmbiguityResolution:
    status: str
    selected: Tuple[AmbiguityCandidate, ...] = ()
    candidates: Tuple[AmbiguityCandidate, ...] = ()
    notes: Tuple[str, ...] = ()

    @property
    def ambiguous(self) -> bool:
        return self.status == "ambiguous"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "ambiguous": self.ambiguous,
            "selected": [item.to_dict() for item in self.selected],
            "candidates": [item.to_dict() for item in self.candidates],
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class CrossSportComparison:
    enabled: bool
    basis: Tuple[str, ...] = ()
    notes: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CrossSportReasoningResult:
    question: str
    route: str
    intent: str
    sport: str = ""
    league: str = ""
    adapter: str = ""
    modules: Tuple[str, ...] = ()
    fused_evidence: Tuple[FusedEvidence, ...] = ()
    ambiguity: AmbiguityResolution = field(default_factory=lambda: AmbiguityResolution("unresolved"))
    comparison: CrossSportComparison = field(default_factory=lambda: CrossSportComparison(False))
    reasoning_steps: Tuple[Dict[str, Any], ...] = ()
    confidence: float = 0.35
    status: str = "pass"
    limitations: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": CROSS_SPORT_REASONING_VERSION,
            "question": self.question,
            "route": self.route,
            "intent": self.intent,
            "sport": self.sport,
            "league": self.league,
            "adapter": self.adapter,
            "modules": list(self.modules),
            "fused_evidence": [item.to_dict() for item in self.fused_evidence],
            "evidence_count": len(self.fused_evidence),
            "ambiguity": self.ambiguity.to_dict(),
            "comparison": self.comparison.to_dict(),
            "reasoning_steps": list(self.reasoning_steps),
            "confidence": round(max(0.0, min(1.0, float(self.confidence))), 4),
            "status": self.status,
            "limitations": list(self.limitations),
        }


__all__ = [
    "CROSS_SPORT_REASONING_VERSION",
    "ReasoningAdapter",
    "FusedEvidence",
    "AmbiguityCandidate",
    "AmbiguityResolution",
    "CrossSportComparison",
    "CrossSportReasoningResult",
]
