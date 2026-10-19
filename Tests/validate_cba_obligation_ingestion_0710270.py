import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Knowledge.Contracts.contract_obligation_acquisition import ingest_contract_obligations
from Reasoning.Cap.cba_obligation_calculator import CapRuleContext

rules = CapRuleContext('fixture', '2026-07-01', '2027-06-30', 'fixture:CBA-rule', 1200000)
base = dict(team_id='TOR', evidence_id='e1', subject_id='player', source_id='src',
            provenance='line1', effective_from='2026-10-01', effective_to='2027-04-01',
            contract_verified=True, status_verified=True, aav=5000000)
payload = dict(team_id='TOR', as_of='2026-10-16', snapshot_id='fixture1',
               roster_verified=False, sources=[dict(id='src', retrieved_at='2026-10-16T10:00:00Z')],
               obligations=[base | dict(status='retained_salary', retention_numerator=1,
                                        retention_denominator=4)])
result = ingest_contract_obligations(payload, cba_rules=rules)
assert result.ledger.charges[0].amount == 1250000
assert result.ledger.charges[0].rule_reference == 'fixture:CBA-rule'
assert result.ledger.verified_cap_charge_total is None
assert not result.ledger.complete
print('PASS: CBA-derived obligation enters canonical ledger without false completeness')
