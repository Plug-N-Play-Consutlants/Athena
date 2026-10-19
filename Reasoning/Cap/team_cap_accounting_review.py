"""Audit a partial NHL cap ledger without inventing full-team cap space.

This is an operational evidence-coverage gate for Scout. It does not calculate
LTIR relief or daily cap accrual from an LTIR designation or a published total.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping

from Reasoning.Cap.canonical_ledger import LedgerReconciliation, REQUIRED_RECONCILIATION


@dataclass(frozen=True)
class TeamCapAccountingReview:
    team_id: str
    as_of: str
    verified_itemized_subtotal: int
    charge_totals: tuple[tuple[str, int], ...]
    charge_counts: tuple[tuple[str, int], ...]
    missing_domains: tuple[str, ...]
    issues: tuple[str, ...]
    published_total: int | None
    published_difference: int | None
    verified_total: int | None
    verified_space: int | None
    complete: bool

    def scout_summary(self) -> str:
        if not self.complete:
            missing = ', '.join(self.missing_domains) or 'unresolved evidence conflicts'
            return (f'{self.team_id} ({self.as_of}): ${self.verified_itemized_subtotal:,} '
                    f'in observed itemized charges, NOT a verified team cap hit. '
                    f'Unresolved: {missing}. '
                    'No certified cap space or transaction affordability calculation is available.')
        return (f'{self.team_id} ({self.as_of}): verified cap charge '
                f'${self.verified_total:,}; verified ceiling headroom '
                f'${self.verified_space:,}. LTIR relief and projected space must be '
                'described separately from ordinary ceiling headroom.')


def review_team_cap_ledger(ledger: LedgerReconciliation, *,
                           cap_ceiling: int | None = None,
                           published_total: int | None = None,
                           published_as_of: str | None = None,
                           published_basis: str | None = None) -> TeamCapAccountingReview:
    """Audit identity, accounting coverage and comparable published figures.

    `published_basis='cap_charge_total'` is required before computing a
    comparison. Projected totals, daily space and LTIR-adjusted figures are
    different measures and cannot be compared to an ordinary charge total.
    """
    if cap_ceiling is not None and (type(cap_ceiling) is not int or cap_ceiling <= 0):
        raise ValueError('Positive integer cap ceiling required')
    if published_total is not None and (type(published_total) is not int or published_total < 0):
        raise ValueError('Published total must be nonnegative integer dollars')
    if published_total is None and (published_as_of is not None or published_basis is not None):
        raise ValueError('Published metadata without published total')
    if published_as_of is not None:
        date.fromisoformat(published_as_of)
    if published_total is not None and (not published_as_of or not published_basis):
        raise ValueError('Published figure requires date and accounting basis')
    totals: dict[str, int] = {}
    counts: dict[str, int] = {}
    issues: list[str] = []
    identity_classes: dict[tuple[str, str], list[str]] = {}
    for charge in ledger.charges:
        if not charge.applies_on(ledger.as_of):
            continue
        totals[charge.charge_class] = totals.get(charge.charge_class, 0) + charge.amount
        counts[charge.charge_class] = counts.get(charge.charge_class, 0) + 1
        identity_classes.setdefault((charge.subject_id, charge.charge_class), []).append(charge.evidence_id)
    # Multiple charges for a subject/class can be legitimate, but require
    # separate obligation identifiers; never silently collapse them.
    for (subject, cls), evidence_ids in identity_classes.items():
        if len(evidence_ids) > 1:
            issues.append(f'Multiple active {cls} entries for {subject}: verify distinct obligations')
    subtotal = sum(totals.values())
    comparable = (published_total is not None and published_as_of == ledger.as_of
                  and published_basis == 'cap_charge_total')
    if published_total is not None and not comparable:
        issues.append('Published figure differs in date or accounting basis; comparison withheld')
    if ledger.verified_ltir_relief is None:
        issues.append('LTIR relief not independently calculated and verified')
    if not ledger.roster_verified:
        issues.append('Full roster and assignments not independently verified')
    missing = tuple(domain for domain in REQUIRED_RECONCILIATION
                    if domain not in ledger.verified_domains)
    # A duplicate active obligation is a substantive accounting conflict even
    # if every domain has otherwise been marked verified.
    complete = ledger.complete and not any(x.startswith('Multiple active') for x in issues)
    verified_total = subtotal if complete else None
    # This is simple headroom, NOT an LTIR-adjusted daily/projected-space value.
    verified_space = cap_ceiling - subtotal if complete and cap_ceiling is not None else None
    return TeamCapAccountingReview(
        ledger.team_id, ledger.as_of, subtotal, tuple(sorted(totals.items())),
        tuple(sorted(counts.items())), missing, tuple(issues), published_total,
        (subtotal - published_total if comparable and complete else None),
        verified_total, verified_space, complete)
