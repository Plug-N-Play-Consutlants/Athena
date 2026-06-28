"""Capability participation audit for AthenaEngine observability.

This v0.5.6.1.0c drop connects the Capability Registry and Execution Trace
Foundation into an actionable diagnostic report. It does not change Scout
routing or response behavior. Its job is to answer: which capabilities were
expected, selected, skipped, missing, or executed, and what evidence gaps made
that answer shallow?
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from Core.capability_registry import CapabilityRegistry, seed_capability_registry
from Core.execution_trace import CapabilityTrace, ExecutionTrace, sample_execution_trace

CAPABILITY_AUDIT_VERSION = "0.5.6.1.0"


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
class CapabilityParticipationRecord:
    """Per-capability audit classification for one execution trace."""

    capability_id: str
    expected: bool = False
    registered: bool = False
    selected: bool = False
    executed: bool = False
    skipped: bool = False
    missing: bool = False
    reason: str = ""
    layer: str = "unknown"
    entrypoints: Tuple[str, ...] = field(default_factory=tuple)
    doctors: Tuple[str, ...] = field(default_factory=tuple)
    validators: Tuple[str, ...] = field(default_factory=tuple)
    evidence_expected: Tuple[str, ...] = field(default_factory=tuple)
    evidence_found: Tuple[str, ...] = field(default_factory=tuple)
    evidence_missing: Tuple[str, ...] = field(default_factory=tuple)
    output_keys: Tuple[str, ...] = field(default_factory=tuple)
    included_output_keys: Tuple[str, ...] = field(default_factory=tuple)
    discarded_output_keys: Tuple[str, ...] = field(default_factory=tuple)
    confidence: float | None = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CapabilityAuditReport:
    """Actionable audit report for a single trace."""

    version: str
    trace_id: str
    prompt: str
    intent: str
    status: str
    expected_count: int
    selected_count: int
    executed_count: int
    skipped_count: int
    missing_count: int
    unregistered_expected_count: int
    evidence_requested_count: int
    evidence_found_count: int
    evidence_missing_count: int
    composition_input_count: int
    composition_output_count: int
    records: Tuple[CapabilityParticipationRecord, ...]
    findings: Tuple[str, ...]
    next_actions: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["records"] = [record.to_dict() for record in self.records]
        return data


def _trace_capability_map(trace: ExecutionTrace) -> Dict[str, CapabilityTrace]:
    return {str(cap.capability_id): cap for cap in trace.capabilities}


def _record_reason(
    capability_id: str,
    *,
    expected: bool,
    registered: bool,
    selected: bool,
    executed: bool,
    skipped: bool,
    trace_cap: CapabilityTrace | None,
) -> str:
    if expected and not registered:
        return "expected capability is not registered/discovered"
    if expected and not selected and not skipped:
        return "expected capability was not selected by the current execution path"
    if skipped:
        return trace_cap.skip_reason if trace_cap and trace_cap.skip_reason else "capability was skipped"
    if selected and not executed:
        return "capability was selected but no execution was recorded"
    if executed:
        return "capability executed"
    if selected:
        return "capability selected"
    return "observed but not part of the expected path"


def audit_execution_trace(
    trace: ExecutionTrace,
    registry: CapabilityRegistry | None = None,
) -> CapabilityAuditReport:
    """Classify expected/actual capability participation for a trace."""
    registry = registry or seed_capability_registry()
    trace_caps = _trace_capability_map(trace)
    expected = set(trace.expected_capabilities)
    selected = set(trace.selected_capabilities)
    skipped = set(trace.skipped_capabilities)
    executed = {cap.capability_id for cap in trace.capabilities if cap.executed}
    all_ids = sorted(expected | selected | skipped | executed | set(trace_caps))

    records: list[CapabilityParticipationRecord] = []
    for capability_id in all_ids:
        meta = registry.get(capability_id)
        trace_cap = trace_caps.get(capability_id)
        is_expected = capability_id in expected or bool(trace_cap and trace_cap.expected)
        is_selected = capability_id in selected or bool(trace_cap and trace_cap.selected)
        is_executed = capability_id in executed or bool(trace_cap and trace_cap.executed)
        is_skipped = capability_id in skipped or bool(trace_cap and trace_cap.skipped)
        is_registered = meta is not None
        is_missing = bool(is_expected and not is_selected and not is_skipped)
        reason = _record_reason(
            capability_id,
            expected=is_expected,
            registered=is_registered,
            selected=is_selected,
            executed=is_executed,
            skipped=is_skipped,
            trace_cap=trace_cap,
        )
        records.append(CapabilityParticipationRecord(
            capability_id=capability_id,
            expected=is_expected,
            registered=is_registered,
            selected=is_selected,
            executed=is_executed,
            skipped=is_skipped,
            missing=is_missing,
            reason=reason,
            layer=meta.layer if meta else "unregistered",
            entrypoints=meta.entrypoints if meta else (),
            doctors=meta.doctors if meta else (),
            validators=meta.validators or meta.tests if meta else (),
            evidence_expected=trace_cap.evidence_expected if trace_cap else (),
            evidence_found=trace_cap.evidence_found if trace_cap else (),
            evidence_missing=trace_cap.evidence_missing if trace_cap else (),
            output_keys=trace_cap.output_keys if trace_cap else (),
            included_output_keys=trace_cap.included_output_keys if trace_cap else (),
            discarded_output_keys=trace_cap.discarded_output_keys if trace_cap else (),
            confidence=trace_cap.confidence if trace_cap else None,
        ))

    missing_records = [record for record in records if record.missing]
    skipped_records = [record for record in records if record.skipped]
    unregistered_expected = [record for record in records if record.expected and not record.registered]
    selected_not_executed = [record for record in records if record.selected and not record.executed]

    findings: list[str] = []
    if missing_records:
        findings.append(f"{len(missing_records)} expected capability/capabilities were not selected.")
    if skipped_records:
        findings.append(f"{len(skipped_records)} capability/capabilities were explicitly skipped.")
    if unregistered_expected:
        findings.append(f"{len(unregistered_expected)} expected capability/capabilities are not registered/discovered.")
    if selected_not_executed:
        findings.append(f"{len(selected_not_executed)} selected capability/capabilities did not record execution.")
    if trace.evidence_missing:
        findings.append(f"{len(trace.evidence_missing)} requested evidence item(s) were missing.")
    if not findings:
        findings.append("All expected capabilities were selected or explicitly accounted for.")

    next_actions: list[str] = []
    if unregistered_expected:
        next_actions.append("Register or implement expected capabilities before tuning routing.")
    if missing_records:
        next_actions.append("Update intent/planner/routing rules so expected capabilities are selected.")
    if skipped_records:
        next_actions.append("Review skip reasons and add evidence or planner rules where appropriate.")
    if trace.evidence_missing:
        next_actions.append("Hydrate missing evidence sources or surface limitations in composition.")
    if not next_actions:
        next_actions.append("Proceed to evidence and composition audit for deeper diagnosis.")

    return CapabilityAuditReport(
        version=CAPABILITY_AUDIT_VERSION,
        trace_id=trace.trace_id,
        prompt=trace.prompt,
        intent=trace.intent,
        status="pass",
        expected_count=len(expected),
        selected_count=len(selected),
        executed_count=len(executed),
        skipped_count=len(skipped_records),
        missing_count=len(missing_records),
        unregistered_expected_count=len(unregistered_expected),
        evidence_requested_count=len(trace.evidence_requested),
        evidence_found_count=len(trace.evidence_found),
        evidence_missing_count=len(trace.evidence_missing),
        composition_input_count=len(trace.composition_inputs),
        composition_output_count=len(trace.composition_outputs),
        records=tuple(records),
        findings=tuple(_unique(findings)),
        next_actions=tuple(_unique(next_actions)),
    )


def sample_capability_audit_report() -> CapabilityAuditReport:
    return audit_execution_trace(sample_execution_trace())


def capability_audit_diagnostics() -> Dict[str, Any]:
    report = sample_capability_audit_report()
    data = report.to_dict()
    data["panel"] = "capability_audit"
    data["supports"] = [
        "expected_vs_actual_capabilities",
        "selected_vs_executed_capabilities",
        "skipped_capability_reasons",
        "unregistered_expected_capabilities",
        "missing_evidence_counts",
        "next_action_recommendations",
    ]
    return data


__all__ = [
    "CAPABILITY_AUDIT_VERSION",
    "CapabilityAuditReport",
    "CapabilityParticipationRecord",
    "audit_execution_trace",
    "capability_audit_diagnostics",
    "sample_capability_audit_report",
]
