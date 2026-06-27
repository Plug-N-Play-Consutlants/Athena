from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class PlayerAssessment:
    """Canonical player assessment object used by Reasoning and Scout.

    The original simple fields remain for backward compatibility. Build 001 adds
    Scout-ready executive assessment sections without requiring AI text
    generation.
    """

    summary: str = ""
    organizational_role: str = ""
    historical_value: str = ""
    trend_value: str = ""
    strengths: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    confidence: float = 0.0

    # Scout Intelligence Layer fields.
    title: str = ""
    executive_summary: str = ""
    current_value: str = ""
    historical_context: str = ""
    trend_analysis: str = ""
    organizational_importance: str = ""
    fantasy_impact: str = ""
    contract_context: str = ""
    risk_assessment: str = ""
    future_outlook: str = ""
    supporting_evidence: List[str] = field(default_factory=list)
    rule_citations: List[Dict[str, Any]] = field(default_factory=list)
    evidence_counts: Dict[str, int] = field(default_factory=dict)
    sections: List[Dict[str, Any]] = field(default_factory=list)
    cards: List[Dict[str, Any]] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "executive_summary": self.executive_summary,
            "organizational_role": self.organizational_role,
            "historical_value": self.historical_value,
            "trend_value": self.trend_value,
            "strengths": list(self.strengths),
            "risks": list(self.risks),
            "opportunities": list(self.opportunities),
            "confidence": self.confidence,
            "current_value": self.current_value,
            "historical_context": self.historical_context,
            "trend_analysis": self.trend_analysis,
            "organizational_importance": self.organizational_importance,
            "fantasy_impact": self.fantasy_impact,
            "contract_context": self.contract_context,
            "risk_assessment": self.risk_assessment,
            "future_outlook": self.future_outlook,
            "supporting_evidence": list(self.supporting_evidence),
            "rule_citations": list(self.rule_citations),
            "evidence_counts": dict(self.evidence_counts),
            "sections": list(self.sections),
            "cards": list(self.cards),
            "limitations": list(self.limitations),
        }
