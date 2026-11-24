"""Period attribution must not overclaim fantasy credit or trade causality."""
import json
from pathlib import Path
from Athena.Investigation.player_level_attribution import analyze_player_attribution, assess_trade_production


def _artifact(root, kind, period, rows, **extra):
    folder=root/kind/'league'/'2026';folder.mkdir(parents=True,exist_ok=True)
    obj={'verified':True,'league_id':'league','season':2026,'period':period,'records':rows,**extra}
    (folder/f'period_{period:03d}.json').write_text(json.dumps(obj))


def test_reconciled_active_points_have_named_contributors(tmp_path):
    _artifact(tmp_path,'PeriodPlayerProduction',6,
              [{'fantrax_player_id':'a','player_name':'Player A','points':3,'goals':1,'assists':2},
               {'fantrax_player_id':'b','player_name':'Player B','points':7,'goals':3,'assists':4}],
              status='verified_nhl_window',roster_basis='verified_historical_period',roster_scope='historical_period:1')
    _artifact(tmp_path,'PeriodRosters',6,
              [{'player_id':'a','owner_team_id':'T','owner_team':'Team T','active_for_period':True},
               {'player_id':'b','owner_team_id':'T','owner_team':'Team T','active_for_period':False}],
              status='verified_period_rosters')
    a=analyze_player_attribution(tmp_path,'league',2026,[6],{5:{'T':10},6:{'T':13}})
    team=a['periods'][0]['teams']['T']
    assert team['status']=='reconciled_active_nhl_points'
    assert team['top_contributors'][0]['name']=='Player A'
    assert team['observed_nhl_points']==3


def test_mismatch_does_not_claim_fantasy_credit(tmp_path):
    _artifact(tmp_path,'PeriodPlayerProduction',6,[{'fantrax_player_id':'a','player_name':'A','points':3}],
              status='verified_nhl_window',roster_basis='verified_historical_period',roster_scope='historical_period:1')
    _artifact(tmp_path,'PeriodRosters',6,[{'player_id':'a','owner_team_id':'T','active_for_period':True}],
              status='verified_period_rosters')
    a=analyze_player_attribution(tmp_path,'league',2026,[6],{5:{'T':10},6:{'T':15}})
    assert a['periods'][0]['teams']['T']['status']=='partial_nhl_evidence_not_fantasy_credit'


def test_missing_snapshot_not_filled_from_latest(tmp_path):
    a=analyze_player_attribution(tmp_path,'league',2026,[6,7,8],{5:{'T':3},6:{'T':5},7:{'T':9},8:{'T':10}})
    assert a['missing_periods']==[6,7,8]


def test_future_effective_trade_has_no_backdated_contribution():
    t=[{'id':'trade14','type':'trade','event_period':8,'roster_effective_period':9}]
    a={'periods':[{'period':8,'teams':{'T':{}}}]}
    assert assess_trade_production(t,a)[0]['status']=='awaiting_roster_effective_period'


def test_post_effective_trade_requires_id_crosswalk():
    t=[{'id':'trade14','type':'trade','roster_effective_period':9}]
    a={'periods':[{'period':9,'teams':{'T':{}}}]}
    assert assess_trade_production(t,a)[0]['status']=='requires_transaction_player_id_crosswalk'


def test_duplicate_ids_fail_closed(tmp_path):
    _artifact(tmp_path,'PeriodPlayerProduction',6,[{'fantrax_player_id':'a','points':2},{'fantrax_player_id':'a','points':2}],
              status='verified_nhl_window',roster_basis='verified_historical_period',roster_scope='h')
    _artifact(tmp_path,'PeriodRosters',6,[{'player_id':'a','owner_team_id':'T','active_for_period':True}],
              status='verified_period_rosters')
    result=analyze_player_attribution(tmp_path,'league',2026,[6],{5:{'T':0},6:{'T':2}})
    assert result['periods'][0]['status']=='duplicate_player_production_ids'
