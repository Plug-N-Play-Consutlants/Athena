"""Runtime bridge that makes investigation strategy operational without putting reasoning in Scout."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Tuple
from .orchestrator import build_investigation_plan
from .state import InvestigationSessionRegistry, InvestigationState
from .evidence_fallback import EvidenceCandidate, EvidenceSelection, select_recent_relevant_evidence

RUNTIME_INTEGRATION_VERSION = "0.6.4.1.0"

@dataclass
class InvestigationRuntimeContext:
    question: str
    intent: str
    plan: object
    state: InvestigationState | None
    continued_state: bool
    evidence_selection: EvidenceSelection | None
    def to_dict(self):
        return {
            "version": RUNTIME_INTEGRATION_VERSION,
            "question": self.question,
            "intent": self.intent,
            "strategy": self.plan.strategy.strategy_id,
            "depth": self.plan.strategy.depth,
            "composition": self.plan.composition.profile,
            "preserve_rich_output": self.plan.composition.preserve_rich_output,
            "unresolved_capabilities": self.plan.unresolved_capabilities,
            "working_investigation": self.state.to_dict() if self.state else None,
            "continued_state": self.continued_state,
            "evidence_selection": self.evidence_selection.to_dict() if self.evidence_selection else None,
        }

def prepare_runtime_context(intent: str, question: str, *, domain="all", session_id="default", entities=(), registry: InvestigationSessionRegistry | None=None, evidence_candidates: Iterable[EvidenceCandidate]=()):
    plan=build_investigation_plan(intent, domain=domain)
    state=None; continued=False
    if plan.create_working_state:
        reg=registry or InvestigationSessionRegistry()
        state, continued=reg.continue_or_start(question, plan.strategy.strategy_id, session_id=session_id, entities=entities)
        state.record_turn()
    selection=None
    if plan.strategy.strategy_id in {"brief_update", "news_update"}:
        selection=select_recent_relevant_evidence(evidence_candidates, requested_entities=entities)
    return InvestigationRuntimeContext(question, intent, plan, state, continued, selection)

def record_runtime_outcome(context: InvestigationRuntimeContext, *, findings=(), open_questions=()):
    if context.state:
        for finding in findings: context.state.add_finding(finding)
        for q in open_questions: context.state.add_open_question(q)
    return context
