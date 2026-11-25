"""Regression: committed scoring audits inform Studio without pretending NHL points are credited."""
import json
from pathlib import Path
from Athena.Investigation.period_evidence_diagnostics import diagnose_period_evidence
from Tools.athena_studio import _evidence_refresh_summary_lines

LEAGUE='testleague'

def _write(root, folder, period, body):
    path = root/folder/LEAGUE/'2026'/f'period_{period:03d}.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body), encoding='utf-8')

def _archives(root, period=8, mismatched=False):
    for folder in ('PeriodPlayerProduction', 'PeriodRosters'):
        _write(root, folder, period, {'verified':True, 'league_id':LEAGUE,'season':'2026','period':period})
    audit = {'schema':'athena.period_attribution.v1', 'league_id':LEAGUE,
             'season':'2025' if mismatched else '2026', 'period':period,
             'eligibility_evidence':'period_roster_snapshot_only_not_game_effective',
             'team_count':2, 'teams':[
                 {'team_id':'A','active_roster_count':15,'numeric_match':True,'difference':0,
                  'unmatched_active_ids':[], 'active_ids_without_nhl_game_rows':['idle']},
                 {'team_id':'B','active_roster_count':15,'numeric_match':False,'difference':-4,
                  'unmatched_active_ids':['unknown1', 'unknown2'], 'active_ids_without_nhl_game_rows':[]} ]}
    _write(root,'PeriodScoringAudit',period,audit)
    return audit

def test_committed_audit_replaces_generic_unverified_join(tmp_path):
    _archives(tmp_path)
    report = diagnose_period_evidence(tmp_path,LEAGUE,2026,[8])['periods'][0]
    assert report['status']=='partial_numeric_reconciliation'
    assert report['scoring_audit_source']=='committed_period_scoring_audit'
    assert (report['numeric_reconciled_teams'],report['discrepant_teams'])==(1,1)
    assert report['total_absolute_point_difference']==4
    assert report['unresolved_active_identity_count']==2
    assert report['active_ids_without_nhl_game_rows']==1
    assert report['game_effective_eligibility_verified'] is False
    assert any('crosswalk' in cause for cause in report['causes_established'])

def test_wrong_season_does_not_become_provenance(tmp_path):
    _archives(tmp_path,mismatched=True)
    report = diagnose_period_evidence(tmp_path,LEAGUE,2026,[8])['periods'][0]
    assert report['status']=='unverified_join'
    assert 'scoring_audit_source' not in report

def test_numeric_match_still_not_credit(tmp_path):
    audit=_archives(tmp_path)
    audit['teams']=audit['teams'][:1]; audit['team_count']=1
    _write(tmp_path,'PeriodScoringAudit',8,audit)
    report=diagnose_period_evidence(tmp_path,LEAGUE,2026,[8])['periods'][0]
    assert report['status']=='numeric_match_not_game_credit_proof'
    assert report['game_effective_eligibility_verified'] is False

def test_studio_exposes_issues_and_provenance(tmp_path):
    _archives(tmp_path)
    report=diagnose_period_evidence(tmp_path,LEAGUE,2026,[8])
    content=json.dumps({'refresh_attempted':True,'acquisition_manifest':{'status':'partial','attempted_count':1},'after':report})
    text='\n'.join(_evidence_refresh_summary_lines(content))
    assert '1/2 teams' in text
    assert 'matched IDs without NHL game rows: 1' in text
    assert 'Provenance: committed period audit' in text
    assert 'NOT proof' in text

def test_malformed_audit_does_not_assert_reconciliation(tmp_path):
    audit=_archives(tmp_path)
    audit['teams'][1]['team_id']='A'
    _write(tmp_path,'PeriodScoringAudit',8,audit)
    report=diagnose_period_evidence(tmp_path,LEAGUE,2026,[8])['periods'][0]
    assert report['status']=='unverified_join'
