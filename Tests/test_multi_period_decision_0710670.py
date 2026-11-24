"""v67 multi-week routing, evidence integrity, and analysis regression."""
from copy import deepcopy
from pytest import raises

from Athena.entry_policy import select_entry_route
from Athena.Investigation.period_execution import _requested_periods
from Athena.Investigation.standings_archive import validate_snapshot
from Athena.Investigation.multi_period_analysis import analyze_snapshots


def _snapshot(p, a, b):
    return {'league_id':'league1','season':2026,'period':p,
            'source':'test','timeframe':'FROM_SEASON_START','complete':True,
            'teams':[{'team_id':'a','name':'A','rank':1 if a>=b else 2,'points':a},
                     {'team_id':'b','name':'B','rank':2 if a>=b else 1,'points':b}]}


def test_composite_prompt_preserves_three_weeks_and_domain():
    q='Compare Weeks 5, 6, and 7 of the JHLPAA. Identify important changes in standings, team performance, transactions, and developing storylines.'
    assert _requested_periods(q)==[5,6,7]
    for mode in ('fantasy','public'):
        assert select_entry_route(q,mode).route=='league_multi_period_analysis'
    assert select_entry_route('Reconcile JHLPAA scoring Weeks 5, 6, and 7').route=='league_recap'


def test_inconsistent_cumulative_rank_is_not_verifiable():
    snap=_snapshot(7,261,262)
    snap['teams'][0]['rank']=1
    snap['teams'][1]['rank']=2
    with raises(ValueError,match='rank/total-points conflict'):
        validate_snapshot(snap)


def test_interval_production_and_reversal_are_period_bounded():
    series=[_snapshot(5,100,95),_snapshot(6,130,145),_snapshot(7,170,160)]
    for snap in series:validate_snapshot(snap)
    original=deepcopy(series)
    out=analyze_snapshots(series,[5,6,7])
    assert out['status']=='verified'
    a=next(t for t in out['teams'] if t['team_id']=='a')
    assert a['ranks']==[1,2,1]
    assert a['interval_points']==[30,40]
    assert series==original
    assert analyze_snapshots(series[:2],[5,6,7])['status']=='missing_periods'
