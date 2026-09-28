"""Sport-neutral investigative scenario contract for evolving claims.

This module deliberately separates what is observed from what is analytically
plausible.  It does not decide truth from source prestige or corroboration count.
Downstream providers may attach contracts, roster constraints, finance, rules,
relationships, or other domain evidence without changing the contract.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

CONTRACT_VERSION = "0.6.5.1.0"

TEMPORAL_EVIDENCE_PRINCIPLES = (
    "Evaluate a conclusion against evidence available when it was made, not later outcomes.",
    "Uncorroborated does not mean false; plausible does not mean true; repeated reporting is not automatically independent corroboration.",
    "Source authority is evidence metadata, not a truth verdict; provenance and underlying evidence remain primary.",
    "Contradictory evidence should trigger investigation and confidence revision rather than automatic dismissal of either side.",
    "A defensible conclusion may later be superseded without having been defective at the time.",
)

INVESTIGATION_STAGES = (
    "claim_provenance",
    "corroboration_and_contradiction",
    "contextual_feasibility",
    "bounded_scenario_analysis",
    "bilateral_impact",
    "current_conclusion",
    "revision_triggers",
)


def build_investigative_contract(*, claim: str, matching_events: Iterable[Dict[str, Any]], context_domains: Iterable[str] | None = None) -> Dict[str, Any]:
    events: List[Dict[str, Any]] = [e for e in matching_events if isinstance(e, dict)]
    independent_sources = []
    for event in events:
        source = str(event.get("source_display_name") or event.get("source") or "").strip()
        if source and source not in independent_sources:
            independent_sources.append(source)
    additional = max(0, len(events) - 1)
    corroboration_state = "single_selected_report" if additional == 0 else "multiple_selected_reports"
    return {
        "contract_version": CONTRACT_VERSION,
        "claim": claim,
        "stages": list(INVESTIGATION_STAGES),
        "corroboration_state": corroboration_state,
        "selected_report_count": len(events),
        "selected_source_count": len(independent_sources),
        "context_domains_requested": list(context_domains or ("rules", "contract_or_finance", "roster_or_organization", "asset_or_counterparty", "relationships")),
        "epistemic_state": "unresolved" if events else "unsupported_in_selected_evidence",
        "temporal_principles": list(TEMPORAL_EVIDENCE_PRINCIPLES),
        "revision_triggers": [
            "independent corroboration or contradiction",
            "primary documents or official findings",
            "material contract/financial evidence",
            "roster, organizational, or counterparty evidence that changes feasibility",
            "a completed, withdrawn, or materially changed underlying event",
        ],
    }
