"""Accounting coverage and non-equivalent source reconciliation regression."""
from Reasoning.Cap.canonical_ledger import CapCharge, LedgerReconciliation, REQUIRED_RECONCILIATION
from Reasoning.Cap.team_cap_accounting_review import review_team_cap_ledger


def charge(evidence, subject, cls, amount):
    return CapCharge(evidence, subject, cls, amount, '2026-07-01', '2027-06-30',
                     'independent:test-source', 'season-effective-rule')

partial = LedgerReconciliation('TOR', '2026-10-17', (
    charge('spc:1', 'nhl:1', 'standard_player_contract', 13000000),
    charge('ret:2', 'nhl:2', 'retained_salary', 1500000)), (), False, 'test:2026-10-17')
review = review_team_cap_ledger(partial, cap_ceiling=104000000,
    published_total=100000000, published_as_of='2026-10-17', published_basis='cap_charge_total')
assert review.verified_itemized_subtotal == 14500000
assert review.verified_total is None and review.verified_space is None
assert review.published_difference is None and not review.complete
assert len(review.missing_domains) == len(REQUIRED_RECONCILIATION)
assert 'NOT a verified team cap hit' in review.scout_summary()
assert dict(review.charge_totals)['retained_salary'] == 1500000

complete = LedgerReconciliation('TOR', '2026-10-17', partial.charges,
    REQUIRED_RECONCILIATION, True, 'verified:2026-10-17', 0)
review = review_team_cap_ledger(complete, cap_ceiling=104000000,
    published_total=15000000, published_as_of='2026-10-17', published_basis='cap_charge_total')
assert review.complete and review.verified_total == 14500000
assert review.verified_space == 89500000 and review.published_difference == -500000
mismatch = review_team_cap_ledger(complete, published_total=15000000,
    published_as_of='2026-10-16', published_basis='projected_cap_hit')
assert mismatch.published_difference is None and mismatch.issues

duplicate = LedgerReconciliation('TOR', '2026-10-17', (
    charge('spc:1', 'nhl:1', 'standard_player_contract', 13000000),
    charge('spc:1b', 'nhl:1', 'standard_player_contract', 13000000)),
    REQUIRED_RECONCILIATION, True, 'verified:2026-10-17', 0)
assert not review_team_cap_ledger(duplicate).complete
for kwargs in ({'published_total': 100},
               {'published_total': 100, 'published_as_of': '2026-10-17'},
               {'cap_ceiling': -1}):
    try:
        review_team_cap_ledger(partial, **kwargs)
    except ValueError:
        pass
    else:
        raise AssertionError('Invalid benchmark accepted')
print('PASS team cap accounting review and Scout coverage gate')
