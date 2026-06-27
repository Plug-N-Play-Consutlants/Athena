"""Player assessor primitive."""
from __future__ import annotations

from typing import Any, Dict, List

from Reasoning.adapters.player_evidence_adapter import (
    build_player_evidence_from_evaluation,
    build_player_profile_from_evaluation,
)
from Reasoning.composition.executive_brief import ExecutiveBriefComposer
from Reasoning.models.player_assessment import PlayerAssessment
from Reasoning.primitives.player_evidence_interpreter import PlayerEvidenceInterpreter
from Reasoning.primitives.player_assessment_builder import PlayerAssessmentBuilder


class PlayerAssessor:
    """Convert a player profile plus evidence into a PlayerAssessment."""

    def __init__(self):
        self.interpreter = PlayerEvidenceInterpreter()
        self.builder = PlayerAssessmentBuilder()
        self.composer = ExecutiveBriefComposer()

    def assess(self, profile: Any = None, evidence_bundle: Any = None) -> PlayerAssessment:
        evaluation: Dict[str, Any] | None = evidence_bundle if isinstance(evidence_bundle, dict) else None

        if evaluation is not None:
            if profile is None:
                profile = build_player_profile_from_evaluation(evaluation)
            evidence = build_player_evidence_from_evaluation(evaluation)
        else:
            evidence = self._coerce_evidence(evidence_bundle)

        findings = self.interpreter.interpret(evidence)
        assessment = self.builder.build(profile, findings)

        # Carry limitation and evidence-count context forward when possible.
        if isinstance(evaluation, dict):
            assessment.limitations = list(evaluation.get("limitations") or [])
            assessment.supporting_evidence = [
                f"{key} evidence"
                for key, value in (evaluation.get("evidence_presence") or {}).items()
                if value
            ]

        brief = self.composer.build_player_brief(
            assessment,
            evaluation=evaluation or {},
            question=(evaluation or {}).get("query", ""),
            mode=(evaluation or {}).get("developer", {}).get("mode", "fantasy") if isinstance((evaluation or {}).get("developer"), dict) else "fantasy",
        )
        self._hydrate_from_brief(assessment, brief)
        return assessment

    def _coerce_evidence(self, evidence_bundle: Any) -> List[Any]:
        evidence = evidence_bundle or []
        if isinstance(evidence, (list, tuple)):
            return list(evidence)

        collected = []
        for attr in (
            "evidence",
            "items",
            "historical_evidence",
            "temporal_evidence",
            "graph_evidence",
            "rule_evidence",
            "contract_evidence",
            "knowledge_pack_evidence",
            "explainability_evidence",
        ):
            value = getattr(evidence, attr, None)
            if value:
                if isinstance(value, (list, tuple)):
                    collected.extend(value)
                else:
                    collected.append(value)
        return collected

    def _hydrate_from_brief(self, assessment: PlayerAssessment, brief: Dict[str, Any]) -> None:
        assessment.title = brief.get("title", assessment.title)
        assessment.executive_summary = brief.get("executive_summary", assessment.executive_summary)
        assessment.summary = brief.get("natural_language_response", assessment.summary)
        assessment.sections = list(brief.get("sections") or [])
        assessment.cards = list(brief.get("cards") or [])
        assessment.evidence_counts = dict(brief.get("evidence_counts") or {})
        assessment.rule_citations = list(brief.get("rule_citations") or assessment.rule_citations)
        assessment.supporting_evidence = list(brief.get("supporting_evidence") or assessment.supporting_evidence)
        for section in assessment.sections:
            heading = str(section.get("heading", "")).lower()
            body = str(section.get("body", ""))
            if heading == "current value":
                assessment.current_value = body
            elif heading == "historical context":
                assessment.historical_context = body
            elif heading == "trend analysis":
                assessment.trend_analysis = body
            elif heading == "organizational importance":
                assessment.organizational_importance = body
            elif heading == "fantasy impact":
                assessment.fantasy_impact = body
            elif heading == "contract context":
                assessment.contract_context = body
            elif heading == "risk assessment":
                assessment.risk_assessment = body
            elif heading == "future outlook":
                assessment.future_outlook = body
