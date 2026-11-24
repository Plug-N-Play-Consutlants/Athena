"""v67.2: newsroom synthesis cannot invent production, trade directions or scope."""
from types import SimpleNamespace
from unittest.mock import patch

from Athena.Investigation.multi_period_analysis import investigate_multi_period
from Scout.conversation.role_intelligence import select_scout_role
from Scout.conversation.multi_period_publication import publish_multi_period

QUESTION='Compare Weeks 5, 6, and 7 of the JHLPAA. Identify changes in standings, performance, transactions, and developing storylines.'


def snapshot(week, scores):
    return {'period':week,'teams':[{'team_id':tid,'name':name,'rank':rank,'points':pts}
                 for tid,name,rank,pts in scores]}


ROWS={
    4:[('a','Bubba',3,52),('b','Southside',5,50),('c','Leader',1,80)],
    5:[('a','Bubba',3,100),('b','Southside',6,79),('c','Leader',1,121)],
    6:[('a','Bubba',2,168),('b','Southside',5,120),('c','Leader',1,174)],
    7:[('a','Bubba',2,196),('b','Southside',5,162),('c','Leader',1,207)],
}


def ctx():
    return SimpleNamespace(league_profile={},standings_archive={},files_loaded=[],transaction_history={'records':[
        {'transaction_id':'t5','status':'completed','season_week':5,'transaction_type':'trade',
         'summary':'Trade completed', 'participants':[{'participant_name':'Bubba'},{'participant_name':'Leader'}],
         'assets':[{'asset_name':'Player One','movement_context':{'from_team_name':'Bubba','to_team_name':'Leader'}},
                   {'asset_name':'Player Two','movement_context':{'from_team_name':'Leader','to_team_name':'Bubba'}}]},
        {'transaction_id':'t6','status':'completed','season_week':6,'transaction_type':'free_agent_add','summary':'Southside added Player Three'}
    ]})


def test_full_window_and_scoring_swing_and_trade_without_motive():
    with patch('Athena.Investigation.multi_period_analysis.resolve_league_context',return_value=('123',2026)),patch(
        'Athena.Investigation.multi_period_analysis.load_snapshot',side_effect=lambda out,l,s,p:snapshot(p,ROWS[p])):
        result=investigate_multi_period(ctx(),QUESTION)
    result_text=result['natural_language_response']
    assert 'Scouting assessment' not in result_text
    assert 'Bubba' in result_text and '68' in result_text and '28' in result_text
    assert '48' in result_text and '144' in result_text  # full window 48 + 68 + 28
    assert 'Week 5: 1 recorded event' in result_text
    assert 'Bubba received Player Two' in result_text
    assert 'Leader received Player One' in result_text
    assert 'Trade completed.' not in result_text
    assert 'caused the change' in result_text
    assert result['developer']['multi_period_findings']['teams_analyzed']==3
    assert result['developer']['multi_period_findings']['scoring_complete']
    assert select_scout_role(QUESTION,intent=result['intent']).role=='journalist'


def test_baseline_gap_never_mislabels_two_week_interval_as_full_three_week_score():
    with patch('Athena.Investigation.multi_period_analysis.resolve_league_context',return_value=('123',2026)),patch(
        'Athena.Investigation.multi_period_analysis.load_snapshot',side_effect=lambda out,l,s,p: (_ for _ in ()).throw(FileNotFoundError('no baseline')) if p==4 else snapshot(p,ROWS[p])):
        result=investigate_multi_period(ctx(),QUESTION)
    assert 'Week 5 production remains unverified' in result['natural_language_response']
    assert not result['developer']['multi_period_findings']['scoring_complete']
    assert 'not a full-window total' in result['natural_language_response']


def test_missing_evidence_has_no_invented_editorial():
    text=publish_multi_period({'status':'missing_periods','periods':[5,6,7]})
    assert 'could not be reconciled' in text
    assert 'The headline' not in text
