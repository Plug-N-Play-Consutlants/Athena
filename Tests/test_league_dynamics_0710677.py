"""v67.7 accepts verified descriptive races and exact rolling window selection."""
from types import SimpleNamespace
from unittest.mock import patch

from Athena.entry_policy import select_entry_route
from Athena.Investigation.league_competitive_dynamics import analyze_competitive_dynamics
from Athena.Investigation.multi_period_analysis import investigate_multi_period
from Scout.conversation.multi_period_publication import publish_multi_period


def _ctx():
    return SimpleNamespace(league_profile={'league_id':'abc','season':2026},standings_archive={},
                           transaction_history={'records':[]},files_loaded=[])


def _snapshot(p):
    scores = [(str(i),f'Team {i:02}',i,220-i*10 + (p-5)*(16-i)) for i in range(1,15)]
    return {'period':p,'teams':[{'team_id':tid,'name':name,'rank':rank,'points':points}
                                  for tid,name,rank,points in scores]}


def test_three_independent_standings_neighborhoods_without_fake_cutoff():
    teams=[{'team_id':str(i),'name':f'Team {i:02}','ranks':[i,i,i],
            'cumulative_points':[220-i*10,236-i*11,252-i*12],
            'window_points':45-i} for i in range(1,15)]
    baseline={'teams':[{'team_id':str(i),'points':200-i*9} for i in range(1,15)]}
    out=analyze_competitive_dynamics(teams,[6,7,8],baseline=baseline)
    assert out['team_count']==14
    assert [g['category'] for g in out['groups']]==['upper_table','middle_table','lower_table']
    assert sum(g['team_count'] for g in out['groups'])==14
    assert out['strategy_attribution'].startswith('unverified')
    text=publish_multi_period({'status':'verified','periods':[6,7,8], 'teams_analyzed':14,
                               'race':{'status':'unavailable'},'competitive_dynamics':out})
    assert 'The middle-table contest' in text and 'The lower-table contest' in text
    assert 'do not establish a playoff cutoff' in text
    assert 'does not establish whether a manager is rebuilding' in text


def test_parenthetical_requested_scope_does_not_swallow_period_five_baseline():
    prompt=('Analyze the JHLPAA across the last three completed scoring periods '
            '(6, 7 and 8), using Period 5 as the baseline. Examine standings and transactions.')
    assert select_entry_route(prompt,'public').route=='league_multi_period_analysis'
    with patch('Athena.Investigation.multi_period_analysis.load_snapshot',side_effect=lambda out,l,s,p:_snapshot(p)):
        result=investigate_multi_period(_ctx(),prompt)
    assert result['developer']['requested_periods']==[6,7,8]
    assert result['developer']['multi_period_findings']['scoring_complete']
    assert result['developer']['period_resolution']['status']=='explicit_completed_window_not_calendar_verified'


def test_missing_period_eight_blocks_publication_instead_of_using_period_seven():
    prompt='Compare Weeks 6, 7 and 8 of the JHLPAA; report standings and trades.'
    def fetch(out,l,s,p):
        if p==8:raise FileNotFoundError('period 8 not synced')
        return _snapshot(p)
    with patch('Athena.Investigation.multi_period_analysis.load_snapshot',side_effect=fetch):
        result=investigate_multi_period(_ctx(),prompt)
    assert result['developer']['requested_periods']==[6,7,8]
    assert result['developer']['multi_period_findings']['status']=='missing_periods'
    assert result['developer']['multi_period_findings']['missing_periods']==[8]
    assert 'Period 8' in result['natural_language_response']
    assert 'could not be reconciled' in result['natural_language_response']
    assert 'The middle-table contest' not in result['natural_language_response']


def test_rolling_window_uses_verified_calendar_not_archive_latest():
    prompt='Analyze the JHLPAA across the last three completed scoring periods. Include standings and trades.'
    with patch('Athena.Investigation.fantrax_period_calendar.acquire_unified_period',
               return_value={'status':'calendar_closed','period':8,'source':'test_calendar','boundary_kind':'scoring','schedule':{9:{'start':'2026-11-24'}}}),patch(
               'Athena.Investigation.multi_period_analysis.load_snapshot',side_effect=lambda out,l,s,p:_snapshot(p)):
        result=investigate_multi_period(_ctx(),prompt)
    assert result['developer']['requested_periods']==[6,7,8]
    assert result['developer']['period_resolution']['active_period']==9


def test_rolling_window_fails_closed_without_calendar():
    prompt='Analyze the JHLPAA across the last three completed scoring periods. Include standings and trades.'
    with patch('Athena.Investigation.fantrax_period_calendar.acquire_unified_period',
               return_value={'status':'unverified','reason':'no scoring schedule'}):
        result=investigate_multi_period(_ctx(),prompt)
    assert result['developer']['requested_periods']==[]
    assert result['developer']['period_resolution']['status']=='unverified'
    assert 'could not be reconciled' in result['natural_language_response']
