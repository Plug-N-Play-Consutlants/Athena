"""Developer trace payloads for Athena orchestration.

The trace is intended for Developer Mode only. Public rendering layers should not
show it directly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .execution_plan import ExecutionPlan, build_execution_plan


DEVELOPER_TRACE_VERSION = "0.5.6.0.0"


@dataclass(frozen=True)
class OrchestrationTrace:
    question: str
    mode: str
    execution_plan: ExecutionPlan
    capabilities_selected: List[str] = field(default_factory=list)
    capabilities_skipped: List[str] = field(default_factory=list)
    evidence_sources: List[str] = field(default_factory=list)
    reasoning_path: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "version": DEVELOPER_TRACE_VERSION,
            "question": self.question,
            "mode": self.mode,
            "intent": self.execution_plan.classified_intent.to_dict(),
            "execution_plan": self.execution_plan.to_dict(),
            "capabilities_selected": list(self.capabilities_selected),
            "capabilities_skipped": list(self.capabilities_skipped),
            "evidence_sources": list(self.evidence_sources),
            "reasoning_path": list(self.reasoning_path),
            "composition_template": self.execution_plan.composition_template,
            "confidence": self.execution_plan.confidence,
            "visibility": "developer_only",
        }


def build_orchestration_trace(question: str, mode: str = "public") -> OrchestrationTrace:
    plan = build_execution_plan(question, mode=mode)
    selected = [step.capability_domain for step in plan.steps if step.required]
    skipped = [step.capability_domain for step in plan.steps if not step.required]
    reasoning_path = [
        "classify_intent",
        "build_execution_plan",
        "select_required_capabilities",
        "defer_optional_capabilities_until_data_available",
        "choose_composition_template",
    ]
    return OrchestrationTrace(
        question=question,
        mode=mode,
        execution_plan=plan,
        capabilities_selected=selected,
        capabilities_skipped=skipped,
        evidence_sources=[],
        reasoning_path=reasoning_path,
    )


def orchestration_diagnostics() -> Dict[str, object]:
    samples = [
        "Tell me about Auston Matthews.",
        "Matthews vs McDavid",
        "How does Gavin McKenna improve the Leafs?",
        "Detroit weaknesses",
    ]
    traces = [build_orchestration_trace(sample, mode="public").to_dict() for sample in samples]
    return {
        "panel": "intent_classification_foundation",
        "version": DEVELOPER_TRACE_VERSION,
        "status": "available",
        "sample_count": len(traces),
        "traces": traces,
        "public_visibility": "hidden",
    }
