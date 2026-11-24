"""Step 4 synthesis: rank evidence without inventing causes or dropping teams."""
from Athena.Investigation.storyline_synthesis import synthesize_storylines
from Athena.Investigation.competitive_race import analyze_race
from Athena.Investigation.multi_period_analysis import investigate_multi_period
from Scout.conversation.multi_period_publication import publish_multi_period
from Tests.test_evidence_to_editorial_0710672 import ROWS, ctx, snapshot, QUESTION
from unittest.mock import patch


def _analysis():
    teams=[]
    for tid,name,_,_ in ROWS[7]:
        points=[next(r[3] for r in ROWS[w] if r[0]==tid) for w in (5,6,7)]
        ranks=[next(r[2] for r in ROWS[w] if r[0]==tid) for w in (5,6,7)]
        weekly={5:points[0]-next(r[3] for r in ROWS[4] if r[0]==tid),6:points[1]-points[0],7:points[2]-points[1]}
        teams.append({'team_id':tid,'name':name,'cumulative_points':points,'ranks':ranks,
            'rank_change':ranks[0]-ranks[-1],'weekly_points':weekly,'window_points':sum(weekly.values())})
    return {'status':'verified','teams':teams,'race':analyze_race(teams,[5,6,7],baseline=snapshot(4,ROWS[4])),
        'transactions':[{'week':5,'count':1,'events':[{'id':'t5','type':'trade','participants':['Bubba','Leader'],
        'received':{'Bubba':['Player Two'],'Leader':['Player One']}}]}]}


def test_ranked_synthesis_preserves_every_team_and_prioritizes_race():
    result=synthesize_storylines(_analysis())
    assert result['status']=='verified'
    assert result['evaluated_teams']==3
    assert len(result['ranked'])==3
    assert result['ranked'][0]['team']=='Bubba'
    assert result['ranked'][0]['kind']=='closing_challenger'
    assert result['ranked'][0]['gap_closed']==17
    assert result['causal_attribution']=='not_established'


def test_trade_is_context_not_claimed_cause():
    result=synthesize_storylines(_analysis())
    bubba=next(t for t in result['ranked'] if t['team']=='Bubba')
    assert len(bubba['trade_context'])==1
    assert bubba['causal_attribution']=='not_established'
    out=publish_multi_period({'status':'verified','periods':[5,6,7], 'teams_analyzed':3,
        'synthesis':result,'race':_analysis()['race']})
    assert 'The competitive storyline' in out
    assert 'has closed 17 points' in out
    assert 'not what caused the change' in out


def test_missing_race_does_not_invent_trajectory():
    data=_analysis()
    data['race']={'status':'unavailable'}
    result=synthesize_storylines(data)
    assert result['status']=='verified'
    assert all(t['kind']=='position_watch' for t in result['ranked'])
    assert all(t['gap_closed'] is None for t in result['ranked'])


def test_invalid_input_does_not_publish_fake_storyline():
    assert synthesize_storylines({'status':'missing_periods'})['featured']==[]
    assert 'The competitive storyline' not in publish_multi_period({'status':'missing_periods','periods':[5,6,7]})


def test_live_integration_exposes_athena_decision_and_scout_publication():
    with patch('Athena.Investigation.multi_period_analysis.resolve_league_context',return_value=('123',2026)),patch(
        'Athena.Investigation.multi_period_analysis.load_snapshot',side_effect=lambda out,l,s,p:snapshot(p,ROWS[p])):
        result=investigate_multi_period(ctx(),QUESTION)
    assert result['developer']['multi_period_findings']['synthesis']['evaluated_teams']==3
    assert 'The competitive storyline' in result['natural_language_response']
    assert 'The transaction wire' in result['natural_language_response']
    assert 'What to watch' in result['natural_language_response']


def test_fourteen_team_cohort_is_analyzed_even_when_only_three_are_featured():
    base=_analysis()
    original=base['teams'][0]
    for index in range(11):
        entry=dict(original)
        entry.update(team_id=f'extra_{index}', name=f'Additional {index}',window_points=20+index)
        base['teams'].append(entry)
    # Each team in verified analysis is scored; the article selects just three.
    result=synthesize_storylines(base)
    assert result['evaluated_teams']==14
    assert len(result['ranked'])==14
    assert len(result['featured'])==3
    assert len({t['team_id'] for t in result['ranked']})==14
