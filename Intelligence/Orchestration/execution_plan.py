"""Execution planning primitives for Athena orchestration v0.5.6.0.0."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .intent_classifier import ClassifiedIntent, classify_request_intent
from .intent_taxonomy import IntentType, definition_for


EXECUTION_PLANNER_VERSION = "0.5.6.0.0"


@dataclass(frozen=True)
class PlanStep:
    step_id: str
    capability_domain: str
    purpose: str
    required: bool = True
    status: str = "planned"

    def to_dict(self) -> Dict[str, object]:
        return {
            "step_id": self.step_id,
            "capability_domain": self.capability_domain,
            "purpose": self.purpose,
            "required": self.required,
            "status": self.status,
        }


@dataclass(frozen=True)
class ExecutionPlan:
    question: str
    mode: str
    classified_intent: ClassifiedIntent
    steps: List[PlanStep] = field(default_factory=list)
    composition_template: str = "default_executive_brief"
    confidence: float = 0.0
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "version": EXECUTION_PLANNER_VERSION,
            "question": self.question,
            "mode": self.mode,
            "intent": self.classified_intent.to_dict(),
            "steps": [step.to_dict() for step in self.steps],
            "composition_template": self.composition_template,
            "confidence": self.confidence,
            "notes": list(self.notes),
        }


def _template_for(intent: IntentType) -> str:
    if intent == IntentType.ORGANIZATIONAL_IMPACT:
        return "organizational_impact_brief"
    if intent in {IntentType.PLAYER_COMPARISON, IntentType.TEAM_COMPARISON}:
        return "comparison_brief"
    if intent in {IntentType.PLAYER_PROFILE, IntentType.TEAM_PROFILE}:
        return "profile_brief"
    if intent in {IntentType.FANTASY_TRADE_ANALYSIS, IntentType.FANTASY_DRAFT_ANALYSIS}:
        return "fantasy_decision_brief"
    if intent == IntentType.ROSTER_CONSTRUCTION:
        return "roster_construction_brief"
    if intent == IntentType.LEAGUE_RULES:
        return "rule_grounded_answer"
    return "default_executive_brief"


def build_execution_plan(question: str, mode: str = "public") -> ExecutionPlan:
    classified = classify_request_intent(question, mode=mode)
    definition = definition_for(classified.primary_intent)
    steps: List[PlanStep] = []

    for index, domain in enumerate(definition.required_capability_domains, start=1):
        steps.append(PlanStep(f"S{index:02d}", domain, f"Required for {classified.primary_intent.value}.", True))

    next_index = len(steps) + 1
    for domain in definition.optional_capability_domains:
        steps.append(PlanStep(f"S{next_index:02d}", domain, f"Optional enhancer for {classified.primary_intent.value}.", False))
        next_index += 1

    if classified.primary_intent == IntentType.ORGANIZATIONAL_IMPACT:
        ordered = [
            ("identity", "Resolve player/team entities before analysis.", True),
            ("player_intelligence", "Assess the player or asset changing the organization.", True),
            ("team_intelligence", "Assess the receiving team's current structure.", True),
            ("roster_construction", "Translate player traits into lineup and depth implications.", False),
            ("salary_cap", "Estimate cap/contract implications when data is available.", False),
            ("competitive_window", "Connect impact to the team's timeline.", False),
            ("reasoning", "Synthesize causal implications across evidence.", True),
            ("response_composition", "Render an executive impact brief.", True),
        ]
        steps = [PlanStep(f"S{i:02d}", domain, purpose, required) for i, (domain, purpose, required) in enumerate(ordered, start=1)]

    notes = [
        "Entities are planning inputs, not routing destinations.",
        f"Response goal: {definition.response_goal}",
    ]
    return ExecutionPlan(
        question=question,
        mode=(mode or "public"),
        classified_intent=classified,
        steps=steps,
        composition_template=_template_for(classified.primary_intent),
        confidence=classified.confidence,
        notes=notes,
    )
