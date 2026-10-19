"""Bounded CBA-governed contract obligation arithmetic.

Rule parameters must be supported by a season-effective CBA reference; this
module does not infer historical thresholds or compute LTIR relief. Calculated
charges still do not establish completeness of a team cap ledger.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from fractions import Fraction
from typing import Mapping, Any

from Reasoning.Cap.canonical_ledger import CapCharge


@dataclass(frozen=True)
class CapRuleContext:
    season: str
    effective_from: str
    effective_to: str
    rule_reference: str
    minor_league_exemption: int

    def __post_init__(self):
        if not self.season or not self.rule_reference.strip():
            raise ValueError('Season and CBA rule provenance required')
        if date.fromisoformat(self.effective_from) > date.fromisoformat(self.effective_to):
            raise ValueError('Reversed CBA rule interval')
        if type(self.minor_league_exemption) is not int or self.minor_league_exemption < 0:
            raise ValueError('Invalid season-specific minor-league exemption')

    def applies(self, start: str, end: str) -> None:
        if not (date.fromisoformat(self.effective_from) <= date.fromisoformat(start)
                <= date.fromisoformat(end) <= date.fromisoformat(self.effective_to)):
            raise ValueError('Charge dates outside CBA rule interval')


def _money(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f'{field} must be nonnegative integer dollars')
    return value


def _fraction(numerator: Any, denominator: Any) -> Fraction:
    if type(numerator) is not int or type(denominator) is not int or denominator <= 0:
        raise ValueError('Retention share must be exact integer numerator/denominator')
    share = Fraction(numerator, denominator)
    if not 0 <= share <= Fraction(1, 2):
        raise ValueError('Retention share outside standard 0-50% range')
    return share


def calculate_contract_charge(row: Mapping[str, Any], rules: CapRuleContext) -> CapCharge:
    """Calculate a supported charge from itemized inputs, not published totals.

    Statuses:
    * active_roster_spc: verified annual cap AAV
    * retained_salary: verified retained fraction of originating AAV
    * buried_contract: max(0, AAV - season-effective exemption)

    No rounding is invented: fractional-dollar outcomes are rejected pending
    an explicitly sourced rounding rule. The caller must independently verify
    the underlying status, contract and retention/assignment facts.
    """
    if not isinstance(row, Mapping):
        raise ValueError('Obligation must be an object')
    start, end = str(row['effective_from']), str(row['effective_to'])
    rules.applies(start, end)
    if row.get('contract_verified') is not True or row.get('status_verified') is not True:
        raise ValueError('Verified contract and applicable status required')
    aav = _money(row['aav'], 'aav')
    status = row['status']
    if status == 'active_roster_spc':
        amount, charge_class = aav, 'standard_player_contract'
    elif status == 'retained_salary':
        share = _fraction(row['retention_numerator'], row['retention_denominator'])
        exact = aav * share
        if exact.denominator != 1:
            raise ValueError('Retention calculation requires sourced dollar-rounding treatment')
        amount, charge_class = exact.numerator, 'retained_salary'
    elif status == 'buried_contract':
        amount = max(0, aav - rules.minor_league_exemption)
        charge_class = 'buried_contract_charge'
    else:
        raise ValueError('Status requires another CBA calculation pathway')
    for field in ('evidence_id', 'subject_id', 'source_id', 'provenance'):
        if not isinstance(row.get(field), str) or not row[field].strip():
            raise ValueError(f'Missing source evidence: {field}')
    return CapCharge(
        evidence_id=row['evidence_id'], subject_id=row['subject_id'],
        charge_class=charge_class, amount=amount,
        effective_from=start, effective_to=end,
        provenance=f"{row['source_id']}:{row['provenance']}",
        rule_reference=rules.rule_reference,
    )
