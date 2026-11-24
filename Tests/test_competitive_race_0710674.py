"""v67.4: check source-backed race positions and partial-window scope."""
from Athena.Investigation.competitive_race import analyze_race
from Scout.conversation.multi_period_publication import publish_multi_period
from Tests.test_evidence_to_editorial_0710672 import ROWS, ctx, snapshot, QUESTION
from Athena.Investigation.multi_period_analysis import investigate_multi_period
from unittest.mock import patch


def teams():
    names={r[0]:r[1] for r in ROWS[7]}
    return [dict(team_id=tid,name=name,ranks=[next(r[2] for r in ROWS[w] if r[0]==tid) for w in (5,6,7)],
            cumulative_points=[next(r[3] for r in ROWS[w] if r[0]==tid) for w in (5,6,7)]) for tid,name in names.items()]


def test_race_from_prior_baseline():
    data=analyze_race(teams(),[5,6,7],baseline=snapshot(4,ROWS[4]))
    assert data['status']=='verified'
    assert data['includes_first_requested_week']
    assert data['leaders']==['Leader']
    assert data['leader_points']==207
    assert data['closest_challengers'][0]['team']=='Bubba'
    assert data['closest_challengers'][0]['end_gap']==11
    assert data['closing_gap'][0]['team']=='Bubba'
    assert data['closing_gap'][0]['gap_closed']==17 # Week4 gap 28, Week7 gap 11
    assert data['losing_ground'][0]['team']=='Southside'
    assert data['losing_ground'][0]['gap_closed']==-15 # Week4 gap30; Week7 gap45


def test_partial_comparison_labels_first_snapshot():
    data=analyze_race(teams(),[5,6,7])
    assert data['comparison_from']=='after Week 5'
    assert not data['includes_first_requested_week']
    assert data['closing_gap'][0]['gap_closed']==10 # Week5 gap21 vs Week7 gap11


def test_tied_lead_never_invents_solo_winner():
    t=teams()
    t[0]['cumulative_points'][-1]=207
    result=analyze_race(t,[5,6,7])
    assert set(result['leaders'])=={'Bubba','Leader'}
    text=publish_multi_period({'status':'verified','periods':[5,6,7],'teams_analyzed':3,'stories':[],'race':result})
    assert 'share the points lead' in text


def test_integrated_publication_has_evidence_backed_race():
    with patch('Athena.Investigation.multi_period_analysis.resolve_league_context',return_value=('123',2026)),patch(
        'Athena.Investigation.multi_period_analysis.load_snapshot',side_effect=lambda out,l,s,p:snapshot(p,ROWS[p])):
        result=investigate_multi_period(ctx(),QUESTION)
    txt=result['natural_language_response']
    assert 'The race for first' in txt
    assert 'Bubba has closed 17 points' in txt
    assert 'Southside has fallen 15 points' in txt
    assert '11 points behind' in txt
    assert 'race' in result['developer']['multi_period_findings']
