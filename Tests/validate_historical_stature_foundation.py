"""Regression: historical stature is evidence-led and never predetermined."""
from Athena.historical_stature import stature_evidence

def evaluate(name, goals, award_count):
    return stature_evidence({'name':name,'awards':[{'trophy':'Rocket Richard Trophy','count':award_count}]},
                            [{'season':'2023-24','gp':81,'goals':goals,'points':100}],
                            {'games':700,'points':800})

for name in ('Auston Matthews','Alexander Mogilny','Connor Bedard','Unknown Prospect'):
    result=evaluate(name,69,3)
    assert result['classification']=='not_determined'
    assert result['status']=='evidence_inventory_only'
    assert any('69 in 81' in x for x in result['supporting_observations'])
    assert len(result['unresolved_tests']) >= 4

assert not stature_evidence({}, [], {})['supporting_observations']
print('[PASS] historical stature evidence inventory; no player-specific classification')
