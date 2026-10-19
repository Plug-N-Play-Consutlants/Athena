from Reasoning.Cap.gm_decision_assessment import assess_gm_decision

def _scenario():
    return {'priorities':{'offense':2,'roster_fit':5}, 'protected_players':['knies'], 'options':[
        {'name':'Marchenko deal','outgoing_players':['knies'],'measures':{'offense':{'value':0.8,'source':'comparison'},'roster_fit':{'value':-0.5,'source':'comparison'}}},
        {'name':'Alternative','outgoing_players':[],'measures':{'offense':{'value':0.3,'source':'comparison'},'roster_fit':{'value':0.7,'source':'comparison'}},'costs':['Asset price unknown']}]}

def test_protected_player_excludes_even_high_score():
    result=assess_gm_decision(_scenario())
    assert result.options[0].eligible is False
    assert result.preferred=='Alternative'
    assert 'protected-player' in result.scout_summary()

def test_changing_objective_changes_ranking_not_evidence():
    data=_scenario(); data['protected_players']=[]
    assert assess_gm_decision(data).preferred=='Alternative'
    data['priorities']={'offense':10}
    assert assess_gm_decision(data).preferred=='Marchenko deal'

def test_missing_source_prevents_ranking():
    data=_scenario(); del data['options'][1]['measures']['offense']['source']
    result=assess_gm_decision(data)
    assert result.options[1].score is None
    assert result.preferred is None

def test_invalid_weights_rejected():
    data=_scenario(); data['priorities']={'offense':-1}
    try: assess_gm_decision(data)
    except ValueError: pass
    else: raise AssertionError('Negative priority accepted')
