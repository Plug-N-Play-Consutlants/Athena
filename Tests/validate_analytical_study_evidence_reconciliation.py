from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from Athena.Reasoning.evidence_reconciliation import reconcile_claim, surviving_hypothesis

root=ROOT
transaction=(root/'Athena/Investigation/nhl_transaction.py').read_text(encoding='utf-8')
composition=(root/'Scout/conversation/composition.py').read_text(encoding='utf-8')
handlers=(root/'Athena/capability_handlers.py').read_text(encoding='utf-8')

assert 'analytical_study_v2' in transaction
for phrase in ('Scenario Assessment','Assets on the Table','What Needs Are We Addressing on Both Sides','Financial Impact',"Athena's Verdict"):
    assert phrase in composition, phrase
assert 'asks_prospects' in handlers and 'query_subset' in handlers
assert 'asks_reluctance' in handlers and 'reluctance_ranking' in handlers
assert 'buyer_decision' in transaction and 'decision_requested' in transaction
assert 'association_only' in (root/'Knowledge/Assets/organizational_rights_state.py').read_text(encoding='utf-8')
assert 'provider prospect association alone is not treated as current legal control' in composition.lower()
claim=reconcile_claim('Partner made a specific comment',independent_support=['later public behavior aligns with the broader proposition'])
assert claim.state=='unresolved'
result=surviving_hypothesis(claim)
assert result['must_not_assert_specific_claim'] is True
assert result['may_support_broader_inference'] is True
print('PASS: analytical study composition, inquiry-specific prospect filtering, and non-binary evidence reconciliation contract.')
