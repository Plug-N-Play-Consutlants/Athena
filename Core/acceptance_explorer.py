"""Acceptance Explorer foundation for AthenaEngine observability.

This v0.5.6.1.0f drop ties together the capability registry, execution
trace, capability participation audit, evidence audit, and composition audit
into one prompt-level diagnostic report. It is observability-only: it does not
change Scout routing, reasoning, provider behavior, or response composition.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, Iterable, Tuple

from Core.capability_registry import CapabilityRegistry, seed_capability_registry
from Core.execution_trace import CapabilityTrace, ExecutionTrace, create_execution_trace, sample_execution_trace
from Core.capability_audit import CapabilityAuditReport, audit_execution_trace
from Core.evidence_audit import EvidenceAuditReport, audit_evidence
from Core.composition_audit import CompositionAuditReport, audit_composition

ACCEPTANCE_EXPLORER_VERSION = "0.5.6.1.0"


def _unique(values: Iterable[str]) -> Tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = str(value or "").strip()
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return tuple(out)


@dataclass(frozen=True)
class AcceptanceExplorerSection:
    """One named section of the acceptance report."""

    section_id: str
    label: str
    status: str
    summary: str
    facts: Tuple[str, ...] = field(default_factory=tuple)
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    next_actions: Tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AcceptanceExplorerReport:
    """One-pane prompt-level acceptance diagnostic."""

    version: str
    trace_id: str
    prompt: str
    mode: str
    intent: str
    entities: Tuple[str, ...]
    status: str
    confidence: float | None
    expected_capabilities: Tuple[str, ...]
    selected_capabilities: Tuple[str, ...]
    skipped_capabilities: Tuple[str, ...]
    missing_expected_capabilities: Tuple[str, ...]
    evidence_requested_count: int
    evidence_found_count: int
    evidence_missing_count: int
    required_evidence_missing_count: int
    optional_evidence_missing_count: int
    generated_section_count: int
    displayed_section_count: int
    discarded_section_count: int
    composition_coverage_ratio: float
    sections: Tuple[AcceptanceExplorerSection, ...]
    findings: Tuple[str, ...]
    next_actions: Tuple[str, ...]
    capability_audit: Dict[str, Any]
    evidence_audit: Dict[str, Any]
    composition_audit: Dict[str, Any]
    final_response_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["sections"] = [section.to_dict() for section in self.sections]
        return data


def _status_from_counts(*, missing_capabilities: int, required_evidence_missing: int, discarded_sections: int) -> str:
    if missing_capabilities or required_evidence_missing:
        return "warn"
    if discarded_sections:
        return "warn"
    return "pass"


def _section_status(has_warning: bool) -> str:
    return "warn" if has_warning else "pass"


def _capability_section(capability_report: CapabilityAuditReport) -> AcceptanceExplorerSection:
    warnings: list[str] = []
    if capability_report.missing_count:
        warnings.append(f"{capability_report.missing_count} expected capability/capabilities were not selected.")
    if capability_report.unregistered_expected_count:
        warnings.append(f"{capability_report.unregistered_expected_count} expected capability/capabilities are not registered.")
    if capability_report.skipped_count:
        warnings.append(f"{capability_report.skipped_count} capability/capabilities were skipped.")
    facts = (
        f"Expected: {capability_report.expected_count}",
        f"Selected: {capability_report.selected_count}",
        f"Executed: {capability_report.executed_count}",
        f"Missing: {capability_report.missing_count}",
        f"Skipped: {capability_report.skipped_count}",
    )
    return AcceptanceExplorerSection(
        section_id="capabilities",
        label="Capability Participation",
        status=_section_status(bool(warnings)),
        summary="Capability participation audit connected expected, selected, skipped, missing, and executed capabilities.",
        facts=facts,
        warnings=tuple(warnings),
        next_actions=capability_report.next_actions,
    )


def _evidence_section(evidence_report: EvidenceAuditReport) -> AcceptanceExplorerSection:
    warnings: list[str] = []
    if evidence_report.required_missing_count:
        warnings.append(f"{evidence_report.required_missing_count} required evidence item(s) are missing.")
    if evidence_report.optional_missing_count:
        warnings.append(f"{evidence_report.optional_missing_count} optional evidence item(s) are missing.")
    facts = (
        f"Requested: {evidence_report.evidence_requested_count}",
        f"Found: {evidence_report.evidence_found_count}",
        f"Missing: {evidence_report.evidence_missing_count}",
        f"Required missing: {evidence_report.required_missing_count}",
        f"Optional missing: {evidence_report.optional_missing_count}",
    )
    return AcceptanceExplorerSection(
        section_id="evidence",
        label="Evidence Audit",
        status=_section_status(bool(warnings)),
        summary="Evidence audit compared capability evidence contracts against evidence actually attached to the trace.",
        facts=facts,
        warnings=tuple(warnings),
        next_actions=evidence_report.next_actions,
    )


def _composition_section(composition_report: CompositionAuditReport) -> AcceptanceExplorerSection:
    warnings: list[str] = []
    if composition_report.discarded_count:
        warnings.append(f"{composition_report.discarded_count} generated section(s) were discarded or not represented.")
    facts = (
        f"Generated: {composition_report.generated_count}",
        f"Displayed: {composition_report.displayed_count}",
        f"Included: {composition_report.included_count}",
        f"Discarded: {composition_report.discarded_count}",
        f"Coverage: {composition_report.coverage_ratio}",
    )
    return AcceptanceExplorerSection(
        section_id="composition",
        label="Composition Audit",
        status=_section_status(bool(warnings)),
        summary="Composition audit measured which generated capability outputs were represented in the final response sections.",
        facts=facts,
        warnings=tuple(warnings),
        next_actions=composition_report.next_actions,
    )


def build_acceptance_report(
    trace: ExecutionTrace | None = None,
    registry: CapabilityRegistry | None = None,
) -> AcceptanceExplorerReport:
    """Build a one-pane acceptance diagnostic from a trace."""
    registry = registry or seed_capability_registry()
    trace = trace or sample_acceptance_trace()
    capability_report = audit_execution_trace(trace, registry=registry)
    evidence_report = audit_evidence(trace)
    composition_report = audit_composition(trace)
    summary = trace.audit_summary()
    missing_expected = tuple(summary.get("missing_expected_capabilities", ()) or ())
    status = _status_from_counts(
        missing_capabilities=len(missing_expected),
        required_evidence_missing=evidence_report.required_missing_count,
        discarded_sections=composition_report.discarded_count,
    )

    findings = _unique(
        tuple(capability_report.findings)
        + tuple(evidence_report.findings)
        + tuple(composition_report.findings)
    )
    next_actions = _unique(
        tuple(capability_report.next_actions)
        + tuple(evidence_report.next_actions)
        + tuple(composition_report.next_actions)
    )

    sections = (
        AcceptanceExplorerSection(
            section_id="execution",
            label="Execution Trace",
            status="pass" if trace.status == "pass" else "warn",
            summary=f"Trace {trace.trace_id} recorded {len(trace.stages)} stage(s) for intent {trace.intent}.",
            facts=(
                f"Prompt: {trace.prompt}",
                f"Mode: {trace.mode}",
                f"Intent: {trace.intent}",
                f"Entities: {', '.join(trace.entities) if trace.entities else 'none'}",
                f"Confidence: {trace.confidence}",
            ),
            warnings=() if trace.status == "pass" else (f"Trace status is {trace.status}.",),
            next_actions=("Use capability/evidence/composition sections to identify divergence.",),
        ),
        _capability_section(capability_report),
        _evidence_section(evidence_report),
        _composition_section(composition_report),
    )

    return AcceptanceExplorerReport(
        version=ACCEPTANCE_EXPLORER_VERSION,
        trace_id=trace.trace_id,
        prompt=trace.prompt,
        mode=trace.mode,
        intent=trace.intent,
        entities=trace.entities,
        status=status,
        confidence=trace.confidence,
        expected_capabilities=trace.expected_capabilities,
        selected_capabilities=trace.selected_capabilities,
        skipped_capabilities=trace.skipped_capabilities,
        missing_expected_capabilities=missing_expected,
        evidence_requested_count=len(trace.evidence_requested),
        evidence_found_count=len(trace.evidence_found),
        evidence_missing_count=len(trace.evidence_missing),
        required_evidence_missing_count=evidence_report.required_missing_count,
        optional_evidence_missing_count=evidence_report.optional_missing_count,
        generated_section_count=composition_report.generated_count,
        displayed_section_count=composition_report.displayed_count,
        discarded_section_count=composition_report.discarded_count,
        composition_coverage_ratio=composition_report.coverage_ratio,
        sections=sections,
        findings=findings,
        next_actions=next_actions,
        capability_audit=capability_report.to_dict(),
        evidence_audit=evidence_report.to_dict(),
        composition_audit=composition_report.to_dict(),
        final_response_summary=trace.final_response_summary,
    )


def sample_acceptance_trace() -> ExecutionTrace:
    """Create an offline-safe acceptance trace that mirrors current Scout pain points."""
    trace = create_execution_trace("How does Gavin McKenna help the Leafs?", mode="public", sample=True)
    trace.intent = "organizational_impact"
    trace.entities = ("Gavin McKenna", "Toronto Maple Leafs")
    trace.expected_capabilities = (
        "player_assessment",
        "team_assessment",
        "roster_assessment",
        "draft_assessment",
        "historical_assessment",
        "reasoning",
        "response_composition",
    )
    trace.selected_capabilities = ("player_assessment", "team_assessment", "reasoning")
    trace.skipped_capabilities = ("roster_assessment", "draft_assessment", "response_composition")
    trace.evidence_requested = ("player_profile", "team_profile", "roster", "draft_picks", "prospects", "salary_cap", "recent_events")
    trace.evidence_found = ("player_profile", "team_profile", "recent_events")
    trace.evidence_missing = ("roster", "draft_picks", "prospects", "salary_cap")
    trace.composition_inputs = ("player_assessment", "team_assessment", "reasoning")
    trace.composition_outputs = ("executive_summary", "limitations")
    trace.final_response_summary = "Fallback public overview was produced instead of a full organizational-impact answer."
    trace.confidence = 0.72
    trace.add_stage("intent", "Intent Classification").complete(detail="organizational_impact", confidence=0.82)
    trace.add_stage("entities", "Entity Resolution").complete(detail="Gavin McKenna + Toronto Maple Leafs", confidence=0.83)
    trace.add_stage("planning", "Execution Planning").complete(detail="partial plan; roster/draft impact not selected", confidence=0.61)
    trace.add_stage("composition", "Response Composition").complete(detail="fallback template selected", confidence=0.58)
    trace.add_capability(CapabilityTrace(
        capability_id="player_assessment",
        expected=True,
        selected=True,
        executed=True,
        evidence_expected=("player_profile", "historical_trends", "draft_context"),
        evidence_found=("player_profile",),
        evidence_missing=("historical_trends", "draft_context"),
        output_keys=("player_profile", "strengths", "draft_impact"),
        included_output_keys=("player_profile",),
        discarded_output_keys=("draft_impact",),
        confidence=0.82,
    ))
    trace.add_capability(CapabilityTrace(
        capability_id="team_assessment",
        expected=True,
        selected=True,
        executed=True,
        evidence_expected=("team_profile", "roster", "salary_cap", "competitive_window"),
        evidence_found=("team_profile",),
        evidence_missing=("roster", "salary_cap", "competitive_window"),
        output_keys=("team_profile", "weaknesses", "competitive_window", "roster_construction"),
        included_output_keys=("team_profile",),
        discarded_output_keys=("weaknesses", "competitive_window", "roster_construction"),
        confidence=0.76,
    ))
    trace.add_capability(CapabilityTrace(
        capability_id="roster_assessment",
        expected=True,
        selected=False,
        executed=False,
        skipped=True,
        skip_reason="planner did not select roster assessment for organizational-impact prompt",
        evidence_expected=("roster", "depth_chart", "salary_cap"),
        evidence_found=(),
        evidence_missing=("roster", "depth_chart", "salary_cap"),
        output_keys=("roster_construction", "line_deployment"),
        discarded_output_keys=("roster_construction", "line_deployment"),
        confidence=None,
    ))
    trace.add_capability(CapabilityTrace(
        capability_id="reasoning",
        expected=True,
        selected=True,
        executed=True,
        evidence_expected=("player_profile", "team_profile", "roster", "draft_picks"),
        evidence_found=("player_profile", "team_profile"),
        evidence_missing=("roster", "draft_picks"),
        output_keys=("executive_summary", "limitations"),
        included_output_keys=("executive_summary", "limitations"),
        confidence=0.7,
    ))
    trace.complete(status="pass", confidence=0.72, final_response_summary=trace.final_response_summary)
    return trace


def sample_acceptance_report() -> AcceptanceExplorerReport:
    return build_acceptance_report(sample_acceptance_trace())


def acceptance_explorer_diagnostics() -> Dict[str, Any]:
    report = sample_acceptance_report()
    data = report.to_dict()
    data["panel"] = "acceptance_explorer"
    data["supports"] = [
        "prompt_level_diagnostics",
        "execution_trace_summary",
        "capability_participation_summary",
        "evidence_gap_summary",
        "composition_gap_summary",
        "single_pane_acceptance_review",
    ]
    return data
