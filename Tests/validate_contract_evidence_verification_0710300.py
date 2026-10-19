"""Deterministic independent SPC corroboration and partial ledger regression."""
from dataclasses import replace
from Knowledge.Contracts.capfreeze_observations import parse_capfreeze_team_text
from Knowledge.Contracts.nhl_roster_evidence import parse_nhl_roster
from Knowledge.Contracts.contract_evidence_verification import verify_contract_observations, ingest_verified_contract_subset
from Tests.validate_capfreeze_observations_0710290 import SAMPLE, URL

observed = parse_capfreeze_team_text('TOR', SAMPLE, source_url=URL, retrieved_at='2026-10-17T00:00:00Z')
roster = parse_nhl_roster({'forwards':[{'id': 1001, 'firstName':{'default':'Auston'}, 'lastName':{'default':'Example'}}], 'defensemen':[], 'goalies':[]}, team_id='TOR', acquired_at='2026-10-17T00:00:00Z', endpoint='https://api-web.nhle.com/v1/roster/TOR/current')
contract = dict(nhl_player_id=1001, player_name='Auston Example', team_id='TOR', aav=13000000, contract_verified=True, status_verified=True, roster_status_verified=True, source_id='independent-contract-record', provenance='https://example.org/authorized-record/1001', rule_reference='effective-dated-SPC-AAV', effective_from='2026-07-01', effective_to='2027-06-30')
result = verify_contract_observations(observed, roster, [contract], as_of='2026-10-17')
assert len(result.matched) == 1 and not result.ledger_complete
assert result.obligations[0]['aav'] == 13000000
ledger = ingest_verified_contract_subset(result, as_of='2026-10-17').ledger
assert len(ledger.charges) == 1 and not ledger.complete and ledger.verified_cap_charge_total is None
changed = verify_contract_observations(observed, roster, [contract | {'aav': 12000000}], as_of='2026-10-17')
assert not changed.matched and changed.discrepancies and not changed.obligations
unverified = verify_contract_observations(observed, roster, [contract | {'contract_verified': False}], as_of='2026-10-17')
assert not unverified.matched and unverified.discrepancies
try:
    verify_contract_observations(observed, roster, [contract, contract], as_of='2026-10-17')
except ValueError: pass
else: raise AssertionError('Duplicate contract identity accepted')
try:
    verify_contract_observations(observed, roster, [contract], as_of='2026-10-01')
except ValueError: pass
else: raise AssertionError('Future-dated publisher evidence accepted')
print('PASS independent contract verification and partial ledger')
