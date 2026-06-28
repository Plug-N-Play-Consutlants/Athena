"""Evidence audit foundation for AthenaEngine observability.

This v0.5.6.1.0d drop answers a narrower question than capability
participation: did each expected capability receive the evidence it needed to
produce a useful answer? It remains observability-only and does not change
Scout routing, reasoning, or response composition.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, Iterable, Mapping, Sequence, Tuple

from Core.execution_trace import CapabilityTrace, ExecutionTrace, sample_execution_trace

EVIDENCE_AUDIT_VERSION = "0.5.6.1.0"


REQUIRED_BY_CAPABILITY: Dict[str, Tuple[str, ...]] = {
    "player_assessment": ("player_profile", "current_season", "team_context"),
    "team_assessment": ("team_profile", "roster", "recent_performance"),
    "roster_assessment": ("roster", "lineup", "injuries"),
    "historical_assessment": ("historical_trends",),
    "trade_assessment": ("assets", "contracts", "team_needs", "counterparty_context"),
    "draft_assessment": ("draft_picks", "prospect_pool", "team_needs"),
    "organizational_impact": ("player_profile", "team_profile", "roster", "competitive_window"),
    "reasoning": ("capability_outputs", "evidence_bundle"),
    "response_composition": ("reasoning_output", "confidence", "limitations"),
}

OPTIONAL_BY_CAPABILITY: Dict[str, Tuple[str, ...]] = {
    "player_assessment": ("injury_history", "deployment", "awards", "international_context"),
    "team_assessment": ("salary_cap", "coach", "transactions", "prospects", "draft_picks"),
    "roster_assessment": ("contracts", "salary_cap", "prospects", "draft_picks"),
    "historical_assessment": ("head_to_head", "age_curve", "recent_delta"),
    "trade_assessment": ("draft_picks", "salary_cap", "manager_tendencies", "market_context"),
    "draft_assessment": ("draft_board", "organizational_depth", "league_scoring"),
    "organizational_impact": ("salary_cap", "prospects", "special_teams", "deployment", "draft_capital"),
    "reasoning": ("event_evidence", "historical_context", "provider_context"),
    "response_composition": ("cards", "source_links", "developer_trace"),
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


def _missing(expected: Iterable[str], found: Iterable[str]) -> Tuple[str, ...]:
    found_set = {str(item) for item in found}
    return tuple(item for item in _unique(expected) if item not in found_set)


@dataclass(frozen=True)
class EvidenceAuditRecord:
    """Evidence coverage for one capability in one execution trace."""

    capability_id: str
    executed: bool = False
    skipped: bool = False
    required_expected: Tuple[str, ...] = field(default_factory=tuple)
    optional_expected: Tuple[str, ...] = field(default_factory=tuple)
    trace_expected: Tuple[str, ...] = field(default_factory=tuple)
    found: Tuple[str, ...] = field(default_factory=tuple)
    missing_required: Tuple[str, ...] = field(default_factory=tuple)
    missing_optional: Tuple[str, ...] = field(default_factory=tuple)
    trace_missing: Tuple[str, ...] = field(default_factory=tuple)
    coverage_ratio: float = 0.0
    confidence_impact: float = 0.0
    status: str = "unknown"
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceAuditReport:
    """Evidence coverage report for a single trace."""

    version: str
    trace_id: str
    prompt: str
    intent: str
    status: str
    evidence_requested_count: int
    evidence_found_count: int
    evidence_missing_count: int
    required_missing_count: int
    optional_missing_count: int
    records: Tuple[EvidenceAuditRecord, ...]
    findings: Tuple[str, ...]
    next_actions: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["records"] = [record.to_dict() for record in self.records]
        return data


def _record_status(required_expected: Sequence[str], missing_required: Sequence[str], found: Sequence[str]) -> str:
    if not required_expected:
        return "informational"
    if len(missing_required) == 0:
        return "pass"
    if found:
        return "partial"
    return "fail"


def _confidence_impact(required_expected: Sequence[str], missing_required: Sequence[str], missing_optional: Sequence[str]) -> float:
    if not required_expected and not missing_optional:
        return 0.0
    required_penalty = 0.12 * len(missing_required)
    optional_penalty = 0.03 * len(missing_optional)
    return round(min(0.75, required_penalty + optional_penalty), 3)


def _reason(status: str, missing_required: Sequence[str], missing_optional: Sequence[str], skipped: bool) -> str:
    if skipped:
        return "capability was skipped; evidence gap may explain why or should be surfaced as a limitation"
    if status == "pass":
        return "required evidence was present"
    if status == "partial":
        return "some evidence was present, but required evidence is missing: " + ", ".join(missing_required)
    if status == "fail":
        return "required evidence was not available: " + ", ".join(missing_required)
    if missing_optional:
        return "optional evidence missing: " + ", ".join(missing_optional)
    return "no declared evidence contract for this capability"


def _capability_records(trace: ExecutionTrace) -> Tuple[EvidenceAuditRecord, ...]:
    records: list[EvidenceAuditRecord] = []
    trace_cap_ids = {cap.capability_id for cap in trace.capabilities}
    synthetic_ids = set(trace.expected_capabilities) - trace_cap_ids
    all_caps: list[CapabilityTrace] = list(trace.capabilities)
    for cap_id in sorted(synthetic_ids):
        all_caps.append(CapabilityTrace(capability_id=cap_id, expected=True))

    trace_found_global = set(trace.evidence_found)
    trace_missing_global = set(trace.evidence_missing)

    for cap in all_caps:
        required_expected = _unique(cap.evidence_expected or REQUIRED_BY_CAPABILITY.get(cap.capability_id, ()))
        optional_expected = _unique(OPTIONAL_BY_CAPABILITY.get(cap.capability_id, ()))
        trace_expected = _unique(cap.evidence_expected)
        found = _unique(cap.evidence_found or tuple(item for item in required_expected if item in trace_found_global))
        missing_required = _unique(cap.evidence_missing or _missing(required_expected, found))
        # Keep missing_required focused on required evidence, not every trace-level missing item.
        missing_required = tuple(item for item in missing_required if item in set(required_expected))
        missing_optional = _missing(optional_expected, found)
        trace_missing = _unique(tuple(item for item in trace.evidence_missing if item in set(required_expected) | set(optional_expected)))
        denom = max(1, len(required_expected))
        coverage = round((len(required_expected) - len(missing_required)) / denom, 3) if required_expected else (1.0 if found else 0.0)
        status = _record_status(required_expected, missing_required, found)
        records.append(EvidenceAuditRecord(
            capability_id=cap.capability_id,
            executed=cap.executed,
            skipped=cap.skipped,
            required_expected=required_expected,
            optional_expected=optional_expected,
            trace_expected=trace_expected,
            found=found,
            missing_required=missing_required,
            missing_optional=missing_optional,
            trace_missing=trace_missing,
            coverage_ratio=coverage,
            confidence_impact=_confidence_impact(required_expected, missing_required, missing_optional),
            status=status,
            reason=_reason(status, missing_required, missing_optional, cap.skipped),
        ))
    return tuple(records)


def audit_evidence(trace: ExecutionTrace) -> EvidenceAuditReport:
    """Build an evidence coverage report from an execution trace."""
    records = _capability_records(trace)
    required_missing = sum(len(record.missing_required) for record in records)
    optional_missing = sum(len(record.missing_optional) for record in records)
    failing = [record for record in records if record.status in {"fail", "partial"}]
    skipped_with_gaps = [record for record in records if record.skipped and (record.missing_required or record.missing_optional)]

    findings: list[str] = []
    if trace.evidence_missing:
        findings.append(f"Trace reports {len(trace.evidence_missing)} missing evidence item(s).")
    if required_missing:
        findings.append(f"Capability evidence contracts are missing {required_missing} required evidence item(s).")
    if optional_missing:
        findings.append(f"{optional_missing} optional evidence item(s) would deepen the answer.")
    if skipped_with_gaps:
        findings.append(f"{len(skipped_with_gaps)} skipped capability/capabilities also had evidence gaps.")
    if not findings:
        findings.append("Required evidence coverage is complete for the sampled trace.")

    next_actions: list[str] = []
    if any("roster" in r.missing_required for r in records):
        next_actions.append("Hydrate roster evidence or make roster absence explicit in Scout composition.")
    if any("draft_picks" in r.missing_required or "draft_picks" in r.missing_optional for r in records):
        next_actions.append("Attach draft-pick and prospect evidence before expecting deep draft/team-makeup answers.")
    if any("salary_cap" in r.missing_optional for r in records):
        next_actions.append("Attach salary-cap evidence for stronger organizational impact and trade analysis.")
    if required_missing:
        next_actions.append("Do not tune prose until missing required evidence is either supplied or surfaced as a limitation.")
    if not next_actions:
        next_actions.append("Proceed to composition audit to see whether available evidence reaches the final response.")

    return EvidenceAuditReport(
        version=EVIDENCE_AUDIT_VERSION,
        trace_id=trace.trace_id,
        prompt=trace.prompt,
        intent=trace.intent,
        status="pass",
        evidence_requested_count=len(trace.evidence_requested),
        evidence_found_count=len(trace.evidence_found),
        evidence_missing_count=len(trace.evidence_missing),
        required_missing_count=required_missing,
        optional_missing_count=optional_missing,
        records=records,
        findings=tuple(_unique(findings)),
        next_actions=tuple(_unique(next_actions)),
    )


def sample_evidence_audit_report() -> EvidenceAuditReport:
    return audit_evidence(sample_execution_trace())


def evidence_audit_diagnostics() -> Dict[str, Any]:
    report = sample_evidence_audit_report()
    data = report.to_dict()
    data["panel"] = "evidence_audit"
    data["supports"] = [
        "required_vs_optional_evidence",
        "found_vs_missing_evidence",
        "capability_level_evidence_coverage",
        "confidence_impact_estimates",
        "evidence_next_action_recommendations",
    ]
    return data


__all__ = [
    "EVIDENCE_AUDIT_VERSION",
    "EvidenceAuditRecord",
    "EvidenceAuditReport",
    "REQUIRED_BY_CAPABILITY",
    "OPTIONAL_BY_CAPABILITY",
    "audit_evidence",
    "evidence_audit_diagnostics",
    "sample_evidence_audit_report",
]
