"""Deterministic provider-neutral ingestion tests; no live claims."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from Knowledge.Contracts.cap_evidence_ingestion import ingest_cap_snapshot
from Reasoning.Cap.canonical_ledger import REQUIRED_RECONCILIATION

def main():
    base = dict(team_id='nhl.team.fixture', as_of='2026-10-16', snapshot_id='fixture:1',
        sources=[dict(id='source-a', retrieved_at='2026-10-16T12:00:00Z')],
        charges=[dict(evidence_id='e1', subject_id='player-a', charge_class='standard_player_contract',
            amount=10_000_000, effective_from='2026-07-01', effective_to='2027-06-30',
            source_id='source-a', provenance='contract-1', rule_reference='fixture:cba-rule')],
        verified_domains=['registered_contracts'], roster_verified=False,
        published_cap_charge_total=11_000_000)
    partial = ingest_cap_snapshot(base)
    assert partial.ledger.verified_cap_charge_total is None
    assert partial.discrepancy is None
    complete = ingest_cap_snapshot({**base, 'verified_domains': list(REQUIRED_RECONCILIATION),
        'roster_verified': True, 'verified_ltir_relief': 0})
    assert complete.ledger.verified_cap_charge_total == 10_000_000
    assert complete.discrepancy == -1_000_000
    for change in ({'sources': []}, {'verified_domains': ['unknown']},
                   {'roster_verified': 'yes'}, {'published_cap_charge_total': 11.5},
                   {'charges': [{**base['charges'][0], 'source_id': 'missing'}]}):
        try: ingest_cap_snapshot({**base, **change})
        except (ValueError, TypeError, KeyError): pass
        else: raise AssertionError(f'Invalid evidence accepted: {change}')
    print('PASS: cap evidence ingestion, provenance, completeness and reconciliation')

if __name__ == '__main__': main()
