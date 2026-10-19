"""Deterministic tests for raw obligation conversion; never claim live coverage."""
from pathlib import Path
import json, sys
from types import SimpleNamespace
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from Knowledge.Contracts.cap_snapshot_acquisition import CapSnapshotSource
from Knowledge.Contracts.contract_obligation_acquisition import (
    build_cap_snapshot_from_obligations, ingest_contract_obligations, acquire_contract_obligations)


def main():
    row = dict(team_id='TOR', evidence_id='spc1', subject_id='p1', source_id='s1',
               provenance='contract', effective_from='2026-07-01', effective_to='2027-06-30',
               rule_reference='CBA:standard-spc', status='active_roster_spc',
               roster_status_verified=True, contract_verified=True, aav=10_000_000)
    base = dict(team_id='TOR', as_of='2026-10-16', snapshot_id='source:2026-10-16',
                sources=[dict(id='s1', retrieved_at='2026-10-16T12:00:00Z')],
                roster_verified=True, obligations=[row], published_cap_charge_total=20_000_000)
    normalized = build_cap_snapshot_from_obligations(base)
    assert normalized['charges'][0]['amount'] == 10_000_000
    assert normalized['verified_domains'] == [] and normalized['roster_verified'] is False
    assert ingest_contract_obligations(base).ledger.verified_cap_charge_total is None
    retained = dict(row, status='retained_salary', evidence_id='r1',
                    cba_charge_verified=True, verified_cap_charge=1_500_000)
    result = ingest_contract_obligations({**base, 'obligations': [row, retained]})
    assert [x.amount for x in result.ledger.charges] == [10_000_000, 1_500_000]
    for bad in (dict(row, roster_status_verified=False),
                dict(row, team_id='MTL'), dict(retained, cba_charge_verified=False),
                dict(row, aav=-1), dict(row, status='ltir')):
        try: ingest_contract_obligations({**base, 'obligations': [bad]})
        except (ValueError, KeyError): pass
        else: raise AssertionError(f'Unsafe contract row accepted: {bad}')
    source = CapSnapshotSource('authorized-contract-feed', 'https://example.org/contracts.json', authorized=True)
    response = acquire_contract_obligations(source, expected_team_id='TOR',
        transport=lambda url, **kwargs: SimpleNamespace(status_code=200, content=json.dumps(base).encode()))
    assert response.ledger.team_id == 'TOR' and not response.ledger.complete
    try: acquire_contract_obligations(source, expected_team_id='MTL',
        transport=lambda url, **kwargs: SimpleNamespace(status_code=200, content=json.dumps(base).encode()))
    except ValueError: pass
    else: raise AssertionError('Cross-team response accepted')
    print('PASS: bounded contract obligations, acquisition, and partial-ledger safety')

if __name__ == '__main__': main()
