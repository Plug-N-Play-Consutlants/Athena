"""Historical eligibility and scoring provenance must not be overstated."""
import json
from Athena.Investigation.period_evidence_diagnostics import diagnose_period_evidence
from Athena.Investigation.player_level_attribution import analyze_player_attribution
from Scout.conversation.multi_period_publication import publish_multi_period


def _write(root, kind, period, records, **fields):
    folder=root/kind/'league'/'2026';folder.mkdir(parents=True,exist_ok=True)
    obj={'verified':True,'league_id':'league','season':'2026','period':period,'records':records,**fields}
    (folder/f'period_{period:03d}.json').write_text(json.dumps(obj))


def _data(tmp_path, score=3):
    _write(tmp_path,'PeriodPlayerProduction',6,[{'fantrax_player_id':'a','player_name':'A','points':3}],
           roster_basis='verified_historical_period',roster_scope='historical-period',status='verified_nhl_window')
    _write(tmp_path,'PeriodRosters',6,[{'player_id':'a','owner_team_id':'T','owner_team':'Team T','active_for_period':True}],
           status='verified_period_rosters')
    return analyze_player_attribution(tmp_path,'league',2026,[6],{5:{'T':10},6:{'T':10+score}})


def test_numeric_equality_is_not_player_fantasy_credit(tmp_path):
    result=_data(tmp_path)
    team=result['periods'][0]['teams']['T']
    assert team['status']=='reconciled_active_nhl_points'
    assert team['credited_fantasy_points_verified'] is False
    assert team['game_effective_eligibility_verified'] is False


def test_diagnostic_preserves_missing_evidence(tmp_path):
    result=_data(tmp_path)
    report=diagnose_period_evidence(tmp_path,'league',2026,[6,8],result)
    assert report['periods'][0]['status']=='numeric_match_not_game_credit_proof'
    assert report['periods'][1]['status']=='missing_period_evidence'
    assert report['periods'][1]['missing_components']==['NHL player-window production','historical period rosters']
    assert report['missing_periods']==[8]


def test_diagnostic_discrepancy_without_invented_cause(tmp_path):
    result=_data(tmp_path, score=5)
    report=diagnose_period_evidence(tmp_path,'league',2026,[6],result)['periods'][0]
    assert report['discrepant_teams']==1
    assert report['total_absolute_point_difference']==2
    assert report['causes_established']==[]
    assert 'game-effective lineup/roster locks' in report['possible_causes_not_proven']


def test_scout_never_says_credit_from_numeric_match():
    data={'status':'verified','periods':[6], 'teams_analyzed':1,
          'player_attribution':{'periods':[{'period':6,'teams':{'T':{'team':'Team T','status':'reconciled_active_nhl_points','credited_fantasy_points_verified':False,'top_contributors':[{'nhl_points':9,'name':'A'}]}}}]},
          'period_evidence_diagnostics':{'periods':[]}}
    article=publish_multi_period(data)
    assert 'Players behind the results' not in article
    assert 'contributed 9 verified' not in article
    assert 'NHL goals-plus-assists' not in article


def test_cli_dry_run_does_not_acquire(tmp_path):
    from Tools.diagnose_period_evidence import run
    r=run(league='league',season=2026,periods=[8],output_dir=tmp_path)
    assert r['refresh_attempted'] is False
    assert r['before']['missing_periods']==[8]
    assert not list(tmp_path.rglob('*'))
