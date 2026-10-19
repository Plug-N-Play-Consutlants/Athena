"""End-to-end *bounded* NHL cap inquiry from acquired contract obligations.

This path intentionally does not certify team cap space from partial sources.
A real complete calculation requires all CBA adjustments and independent
coverage verification; publisher projections are comparison evidence only.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping
from Knowledge.Contracts.contract_obligation_acquisition import ingest_contract_obligations
from Reasoning.Cap.cba_obligation_calculator import CapRuleContext
from Reasoning.Cap.team_cap_accounting_review import TeamCapAccountingReview, review_team_cap_ledger
from Reasoning.Cap.gm_decision_assessment import assess_gm_decision, GMDecisionAssessment
from Reasoning.Cap.historical_decision_reconstruction import reconstruct_historical_decision, HistoricalDecisionAssessment
from Reasoning.Cap.roster_move_assessment import assess_roster_move, RosterMoveAssessment, assess_roster_sequence, SequencedRosterAssessment

@dataclass(frozen=True)
class CapInquiryResult:
    review: TeamCapAccountingReview
    evidence_count: int
    unresolved: tuple[str, ...]
    roster_moves: tuple[RosterMoveAssessment, ...] = ()
    roster_sequence: SequencedRosterAssessment | None = None
    gm_decision: GMDecisionAssessment | None = None
    historical_decision: HistoricalDecisionAssessment | None = None
    def scout_answer(self) -> str:
        prefix = self.review.scout_summary()
        if self.unresolved:
            prefix += ' Evidence requiring investigation: ' + '; '.join(self.unresolved) + '.'
        if self.roster_moves:
            prefix += ' Roster scenarios: ' + ' '.join(m.scout_summary() for m in self.roster_moves)
        if self.roster_sequence is not None:
            prefix += " " + self.roster_sequence.scout_summary()
        if self.gm_decision is not None:
            prefix += " " + self.gm_decision.scout_summary()
        if self.historical_decision is not None:
            prefix += " " + self.historical_decision.scout_summary()
        return prefix

def execute_cap_inquiry(payload: Mapping[str, Any], *, cba_rules: CapRuleContext,
                        cap_ceiling: int, published_total: int | None = None,
                        published_as_of: str | None = None,
                        published_basis: str | None = None) -> CapInquiryResult:
    """Execute a contract-evidence-to-Scout inquiry, retaining evidence gaps.

    `payload` must originate from an authorized, independently corroborated
    source acquisition path. No external API is invented or silently invoked.
    """
    if payload.get('as_of') is None or not isinstance(payload.get('obligations'), list):
        raise ValueError('Dated itemized contract evidence required')
    acquired = ingest_contract_obligations(payload, cba_rules=cba_rules)
    ledger = acquired.ledger
    review = review_team_cap_ledger(ledger, cap_ceiling=cap_ceiling,
                                    published_total=published_total,
                                    published_as_of=published_as_of,
                                    published_basis=published_basis)
    unresolved = list(review.issues)
    if not payload['obligations']:
        unresolved.append('No itemized contracts acquired')
    for domain in review.missing_domains:
        unresolved.append('Unverified accounting domain: ' + domain)
    if published_total is not None and review.published_difference is not None and review.published_difference != 0:
        unresolved.append(f'Independent benchmark differs by ${review.published_difference:,}')
    moves = payload.get("proposed_roster_moves", [])
    if not isinstance(moves, list):
        raise ValueError("Roster scenarios must be a list")
    assessments = tuple(assess_roster_move(move, minor_league_exemption=cba_rules.minor_league_exemption) for move in moves)
    sequence = assess_roster_sequence(moves, minor_league_exemption=cba_rules.minor_league_exemption) if moves else None
    gm = assess_gm_decision(payload["gm_scenario"]) if "gm_scenario" in payload else None
    historical = reconstruct_historical_decision(payload["historical_decision"]) if "historical_decision" in payload else None
    return CapInquiryResult(review, len(ledger.charges), tuple(dict.fromkeys(unresolved)), assessments, sequence, gm, historical)
