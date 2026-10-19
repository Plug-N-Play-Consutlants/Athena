"""Source-traceable NHL team cap ledger arithmetic.

This module totals *verified cap charges*, not raw salary/AAV or roster counts.
CBA-dependent transformations (LTIR, buried charges, bonuses, retention, etc.)
must be calculated upstream using effective-dated rules and supported evidence.
An LTIR designation alone does not authorize an increased ceiling or relief.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Tuple

CHARGE_CLASSES = (
    "standard_player_contract", "retained_salary", "buried_contract_charge",
    "buyout_or_termination_charge", "bonus_overage", "other_cap_charge",
)
REQUIRED_RECONCILIATION = (
    "registered_contracts", "roster_and_assignments", "retained_salary",
    "buried_contracts", "buyouts_and_terminations", "bonuses_and_overages",
    "ltir_and_relief", "other_adjustments",
)

@dataclass(frozen=True)
class CapCharge:
    evidence_id: str
    subject_id: str
    charge_class: str
    amount: int  # integer dollars of cap charge, NOT nominal salary
    effective_from: str
    effective_to: str
    provenance: str
    rule_reference: str

    def __post_init__(self):
        if not self.evidence_id or not self.subject_id or not self.provenance or not self.rule_reference:
            raise ValueError("Every cap charge needs identity, source provenance and applicable rule")
        if self.charge_class not in CHARGE_CLASSES:
            raise ValueError(f"Unsupported charge class: {self.charge_class}")
        if type(self.amount) is not int or self.amount < 0:
            raise ValueError("Cap charge must be a nonnegative integer-dollar amount")
        if date.fromisoformat(self.effective_from) > date.fromisoformat(self.effective_to):
            raise ValueError("Charge effective dates are reversed")

    def applies_on(self, as_of: str) -> bool:
        day = date.fromisoformat(as_of)
        return date.fromisoformat(self.effective_from) <= day <= date.fromisoformat(self.effective_to)

@dataclass(frozen=True)
class LedgerReconciliation:
    team_id: str
    as_of: str
    charges: Tuple[CapCharge, ...]
    verified_domains: Tuple[str, ...]
    roster_verified: bool
    source_snapshot: str
    # Effective-dated, CBA-validated relief amount, NOT the player's cap hit.
    verified_ltir_relief: int | None = None

    def __post_init__(self):
        date.fromisoformat(self.as_of)
        if not self.team_id or not self.source_snapshot:
            raise ValueError("Team identity and dated source snapshot are required")
        if self.verified_ltir_relief is not None and (type(self.verified_ltir_relief) is not int or self.verified_ltir_relief < 0):
            raise ValueError("Verified LTIR relief must be nonnegative integer dollars")
        ids = [charge.evidence_id for charge in self.charges]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate cap-charge evidence IDs")
        unknown = set(self.verified_domains) - set(REQUIRED_RECONCILIATION)
        if unknown:
            raise ValueError(f"Unknown reconciliation domains: {sorted(unknown)}")

    @property
    def missing_domains(self) -> Tuple[str, ...]:
        return tuple(x for x in REQUIRED_RECONCILIATION if x not in self.verified_domains)

    @property
    def complete(self) -> bool:
        return self.roster_verified and not self.missing_domains and self.verified_ltir_relief is not None

    @property
    def verified_cap_charge_total(self) -> int | None:
        if not self.complete:
            return None
        return sum(x.amount for x in self.charges if x.applies_on(self.as_of))

    def reconcile(self, published_cap_charge_total: int) -> int | None:
        """Difference from a third-party total; not an automatic correction."""
        total = self.verified_cap_charge_total
        return None if total is None else total - int(published_cap_charge_total)
