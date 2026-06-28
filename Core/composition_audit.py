"""Composition audit foundation for AthenaEngine observability.

This v0.5.6.1.0e drop answers the next question after capability and
evidence audits: did capability output actually make it into the final Scout
response? It is observability-only and does not change routing, reasoning, or
response prose.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, Iterable, Mapping, Sequence, Tuple

from Core.execution_trace import CapabilityTrace, ExecutionTrace, create_execution_trace, sample_execution_trace

COMPOSITION_AUDIT_VERSION = "0.5.6.1.0"


SECTION_ALIASES: Dict[str, Tuple[str, ...]] = {
    "executive_summary": ("summary", "overview", "conclusion"),
    "player_profile": ("profile", "player", "identity"),
    "team_profile": ("team", "identity", "organizational_identity"),
    "strengths": ("strength", "positive", "why_they_can_be_good"),
    "weaknesses": ("weakness", "risk", "what_can_hold_them_back"),
    "historical_trends": ("history", "historical", "trend"),
    "roster_construction": ("roster", "lineup", "depth"),
    "competitive_window": ("window", "future", "outlook"),
    "draft_impact": ("draft", "prospect", "pick"),
    "trade_analysis": ("trade", "asset", "counterparty"),
    "limitations": ("limitation", "missing", "uncertainty"),
}


def _unique(values: Iterable[str]) -> Tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = str(value or "").strip()
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return tuple(out)


def _normalize_key(value: str) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def _section_matches(output_key: str, displayed_sections: Sequence[str]) -> bool:
    key = _normalize_key(output_key)
    displayed = {_normalize_key(item) for item in displayed_sections}
    if key in displayed:
        return True
    aliases = SECTION_ALIASES.get(key, ())
    if any(_normalize_key(alias) in displayed for alias in aliases):
        return True
    for section in displayed:
        normalized = _normalize_key(section)
        if key and (key in normalized or normalized in key):
            return True
        if any(_normalize_key(alias) in normalized for alias in aliases):
            return True
    return False


def _discard_reason(capability: CapabilityTrace, output_key: str, displayed_sections: Sequence[str]) -> str:
    if capability.skipped:
        return capability.skip_reason or "capability skipped before composition"
    if not capability.executed:
        return "capability did not execute, so no output reached composition"
    if output_key in capability.discarded_output_keys:
        return "capability explicitly marked output as discarded"
    if not displayed_sections:
        return "trace did not record displayed composition sections"
    return "generated output was not matched to any displayed composition section"


@dataclass(frozen=True)
class CompositionAuditRecord:
    """Composition coverage for one capability in one execution trace."""

    capability_id: str
    executed: bool = False
    skipped: bool = False
    generated_sections: Tuple[str, ...] = field(default_factory=tuple)
    displayed_sections: Tuple[str, ...] = field(default_factory=tuple)
    included_sections: Tuple[str, ...] = field(default_factory=tuple)
    discarded_sections: Tuple[str, ...] = field(default_factory=tuple)
    coverage_ratio: float = 0.0
    status: str = "unknown"
    discard_reasons: Tuple[str, ...] = field(default_factory=tuple)
    confidence: float | None = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CompositionAuditReport:
    """Composition audit report for a single trace."""

    version: str
    trace_id: str
    prompt: str
    intent: str
    status: str
    generated_count: int
    displayed_count: int
    included_count: int
    discarded_count: int
    coverage_ratio: float
    records: Tuple[CompositionAuditRecord, ...]
    findings: Tuple[str, ...]
    next_actions: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["records"] = [record.to_dict() for record in self.records]
        return data


def _record_for_capability(capability: CapabilityTrace, displayed_sections: Sequence[str]) -> CompositionAuditRecord:
    generated = _unique(capability.output_keys)
    explicit_included = _unique(capability.included_output_keys)
    explicit_discarded = _unique(capability.discarded_output_keys)
    matched_included = tuple(section for section in generated if _section_matches(section, displayed_sections))
    included = _unique(explicit_included + matched_included)
    discarded = _unique(explicit_discarded + tuple(section for section in generated if section not in included))
    denom = max(1, len(generated))
    coverage = round(len(included) / denom, 3) if generated else 0.0
    if not generated and capability.skipped:
        status = "skipped"
    elif not generated:
        status = "no_output"
    elif discarded and included:
        status = "partial"
    elif discarded and not included:
        status = "discarded"
    else:
        status = "pass"
    reasons = tuple(_discard_reason(capability, section, displayed_sections) for section in discarded)
    return CompositionAuditRecord(
        capability_id=capability.capability_id,
        executed=capability.executed,
        skipped=capability.skipped,
        generated_sections=generated,
        displayed_sections=_unique(displayed_sections),
        included_sections=included,
        discarded_sections=discarded,
        coverage_ratio=coverage,
        status=status,
        discard_reasons=_unique(reasons),
        confidence=capability.confidence,
    )


def audit_composition(trace: ExecutionTrace) -> CompositionAuditReport:
    """Build a composition coverage report from an execution trace."""
    displayed = _unique(trace.composition_outputs)
    records = tuple(_record_for_capability(cap, displayed) for cap in trace.capabilities)
    generated_sections = _unique(section for record in records for section in record.generated_sections)
    included_sections = _unique(section for record in records for section in record.included_sections)
    discarded_sections = _unique(section for record in records for section in record.discarded_sections)
    denom = max(1, len(generated_sections))
    coverage = round(len(included_sections) / denom, 3) if generated_sections else 0.0

    findings: list[str] = []
    if discarded_sections:
        findings.append(f"{len(discarded_sections)} generated section(s) did not appear in the recorded composition output.")
    if any(record.status == "skipped" for record in records):
        findings.append("One or more capabilities were skipped before composition could use their output.")
    if displayed and not generated_sections:
        findings.append("Composition output was recorded, but no capability output keys were attached to the trace.")
    if not findings:
        findings.append("Recorded capability outputs are represented in composition.")

    next_actions: list[str] = []
    if any("weakness" in section for section in discarded_sections):
        next_actions.append("Review response templates that suppress weakness/risk sections.")
    if any("historical" in section or "trend" in section for section in discarded_sections):
        next_actions.append("Ensure historical/trend outputs have matching composition sections.")
    if any("roster" in section or "draft" in section or "trade" in section for section in discarded_sections):
        next_actions.append("Add or map roster/draft/trade output sections before expecting deep team-makeup answers.")
    if discarded_sections:
        next_actions.append("Use composition audit before adding new intelligence; the output may already exist but be dropped.")
    if not next_actions:
        next_actions.append("Proceed to acceptance-level trace comparison.")

    return CompositionAuditReport(
        version=COMPOSITION_AUDIT_VERSION,
        trace_id=trace.trace_id,
        prompt=trace.prompt,
        intent=trace.intent,
        status="pass",
        generated_count=len(generated_sections),
        displayed_count=len(displayed),
        included_count=len(included_sections),
        discarded_count=len(discarded_sections),
        coverage_ratio=coverage,
        records=records,
        findings=tuple(findings),
        next_actions=tuple(next_actions),
    )


def sample_composition_audit_report() -> CompositionAuditReport:
    """Build an offline-safe sample composition audit report."""
    trace = create_execution_trace("How does Gavin McKenna help the Leafs?", mode="public", sample=True)
    trace.intent = "organizational_impact"
    trace.entities = ("Gavin McKenna", "Toronto Maple Leafs")
    trace.expected_capabilities = ("player_assessment", "team_assessment", "roster_assessment", "reasoning", "response_composition")
    trace.selected_capabilities = ("player_assessment", "team_assessment", "reasoning")
    trace.skipped_capabilities = ("roster_assessment", "response_composition")
    trace.composition_inputs = ("player_assessment", "team_assessment", "reasoning")
    trace.composition_outputs = ("executive_summary", "limitations")
    trace.add_capability(CapabilityTrace(
        capability_id="player_assessment",
        expected=True,
        selected=True,
        executed=True,
        output_keys=("player_profile", "strengths", "deployment", "draft_impact"),
        included_output_keys=("player_profile",),
        discarded_output_keys=("deployment", "draft_impact"),
        confidence=0.82,
    ))
    trace.add_capability(CapabilityTrace(
        capability_id="team_assessment",
        expected=True,
        selected=True,
        executed=True,
        output_keys=("team_profile", "weaknesses", "competitive_window", "roster_construction"),
        included_output_keys=("team_profile",),
        discarded_output_keys=("weaknesses", "competitive_window", "roster_construction"),
        confidence=0.78,
    ))
    trace.add_capability(CapabilityTrace(
        capability_id="reasoning",
        expected=True,
        selected=True,
        executed=True,
        output_keys=("executive_summary", "limitations"),
        included_output_keys=("executive_summary", "limitations"),
        confidence=0.68,
    ))
    trace.add_capability(CapabilityTrace(
        capability_id="roster_assessment",
        expected=True,
        selected=False,
        executed=False,
        skipped=True,
        skip_reason="not selected by current planner/routing path",
    ))
    trace.complete(status="pass", confidence=0.68, final_response_summary="Sample composition audit trace")
    return audit_composition(trace)


def composition_audit_diagnostics() -> Dict[str, Any]:
    report = sample_composition_audit_report()
    return {
        "panel": "composition_audit",
        "version": COMPOSITION_AUDIT_VERSION,
        "status": report.status,
        "trace_id": report.trace_id,
        "prompt": report.prompt,
        "intent": report.intent,
        "generated_count": report.generated_count,
        "displayed_count": report.displayed_count,
        "included_count": report.included_count,
        "discarded_count": report.discarded_count,
        "coverage_ratio": report.coverage_ratio,
        "records": [record.to_dict() for record in report.records],
        "findings": list(report.findings),
        "next_actions": list(report.next_actions),
        "supports": [
            "generated_vs_displayed_sections",
            "discarded_output_tracking",
            "capability_output_attribution",
            "composition_coverage_ratio",
            "template_gap_diagnosis",
        ],
    }


__all__ = [
    "COMPOSITION_AUDIT_VERSION",
    "CompositionAuditRecord",
    "CompositionAuditReport",
    "audit_composition",
    "composition_audit_diagnostics",
    "sample_composition_audit_report",
]
