"""Offline tests for explicit, bounded acquisition and canonical integration."""
from pathlib import Path
import json
import sys
from types import SimpleNamespace
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from Knowledge.Contracts.cap_snapshot_acquisition import CapSnapshotSource, acquire_cap_snapshot


def main():
    source = CapSnapshotSource('authorized-test', 'https://example.org/nhl/cap.json', authorized=True)
    payload = dict(team_id='TOR', as_of='2026-10-16', snapshot_id='test-snapshot',
                   sources=[dict(id='s1', retrieved_at='2026-10-16T20:00:00Z')],
                   charges=[dict(evidence_id='e1', subject_id='p1', charge_class='standard_player_contract',
                                 amount=10000000, effective_from='2026-07-01', effective_to='2027-06-30',
                                 source_id='s1', provenance='contract', rule_reference='cba:test')],
                   verified_domains=['registered_contracts'], roster_verified=False)
    calls = []
    def transport(url, **kwargs):
        calls.append((url, kwargs))
        return SimpleNamespace(status_code=200, content=json.dumps(payload).encode())
    result = acquire_cap_snapshot(source, transport=transport, expected_team_id='TOR', expected_as_of='2026-10-16')
    assert result.ledger.team_id == 'TOR' and result.ledger.verified_cap_charge_total is None
    assert calls[0][1]['allow_redirects'] is False and calls[0][1]['timeout'] == 15
    for url in ('http://example.org/cap', 'https://localhost/cap', 'https://127.0.0.1/cap',
                'https://user:pass@example.org/cap'):
        try: CapSnapshotSource('test', url, authorized=True)
        except ValueError: pass
        else: raise AssertionError(f'Unsafe URL accepted: {url}')
    try: CapSnapshotSource('test', 'https://example.org/cap')
    except ValueError: pass
    else: raise AssertionError('Unauthorized source accepted')
    try: acquire_cap_snapshot(source, transport=transport, expected_team_id='MTL')
    except ValueError: pass
    else: raise AssertionError('Mismatched team accepted')
    print('PASS: bounded cap snapshot acquisition and canonical ingestion')

if __name__ == '__main__': main()
