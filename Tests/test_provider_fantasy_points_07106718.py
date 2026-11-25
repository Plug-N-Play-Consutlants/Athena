"""Provider scoring must not depend on NHL or an inferred G+A=FPts equation."""
import json
from pathlib import Path
import pytest
from Athena.Investigation.provider_fantasy_points import (
    normalize_provider_period, load_provider_period, analyze_provider_points)
from Scout.conversation.multi_period_publication import publish_multi_period


def ledger(period=6, provider='fantrax', points=7):
    return {'schema':'athena.provider_period_fantasy_points.v1','provider':provider,
            'league_id':'league','season':'2026','period':period,
            'verified':True,'status':'provider_credited_period',
            'source':'authenticated_provider_period_player_stats',
            'records':[{'player_id':'p1','player_name':'Example Player','team_id':'T',
                        'team_name':'Team T','fantasy_points':points,
                        'credit_basis':'provider_period_credited'}]}


def _save(root, body):
    p=root/'PeriodFantasyPoints'/body['provider']/'league'/'2026'/f"period_{body['period']:03d}.json"
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(body),encoding='utf-8')


def test_provider_points_are_not_nhl_points(tmp_path):
    _save(tmp_path,ledger(points=17.25))
    report=analyze_provider_points(tmp_path,provider='fantrax',league='league',season=2026,periods=[6],team_ids={'T'})
    assert report['periods'][0]['leaders'][0]['fantasy_points']==17.25
    assert report['available_periods']==[6]


def test_other_provider_with_different_scoring(tmp_path):
    _save(tmp_path,ledger(provider='yahoo',points=27.5))
    assert load_provider_period(tmp_path,'yahoo','league',2026,6)['records'][0]['fantasy_points']==27.5


@pytest.mark.parametrize('change',[
    {'period':7}, {'season':'2025'}, {'provider':'yahoo'}, {'league_id':'other'},
    {'verified':False}, {'status':'unverified'}, {'source':None},
])
def test_wrong_identity_or_provenance_rejected(change):
    data=ledger(); data.update(change)
    with pytest.raises(ValueError): normalize_provider_period(data,provider='fantrax',league='league',season=2026,period=6)


def test_ytd_or_nhl_stats_cannot_masquerade_as_period_credit():
    data=ledger();data['records'][0]['credit_basis']='season_ytd'
    with pytest.raises(ValueError):normalize_provider_period(data,provider='fantrax',league='league',season=2026,period=6)


def test_duplicate_player_and_unknown_owner_rejected(tmp_path):
    data=ledger();data['records'].append(dict(data['records'][0]))
    with pytest.raises(ValueError):normalize_provider_period(data,provider='fantrax',league='league',season=2026,period=6)
    data['records']=data['records'][:1];data['records'][0]['team_id']='unknown';_save(tmp_path,data)
    r=analyze_provider_points(tmp_path,provider='fantrax',league='league',season=2026,periods=[6],team_ids={'T'})
    assert r['periods'][0]['status']=='unknown_historical_team'


def test_no_nhl_fallback_or_automatic_audit_prose():
    article_data={'status':'verified','periods':[6,7],'teams_analyzed':1,
                  'race':{'status':'unavailable'},'stories':[], 'transactions':[],
                  'player_attribution':{'periods':[{'period':6,'teams':{'T':{'team':'Team T',
                    'top_contributors':[{'name':'NHL Only','nhl_points':20}]}}}]},
                  'period_evidence_diagnostics':{'periods':[{'period':6,'status':'partial_numeric_reconciliation','discrepant_teams':2,'team_count':14}]},
                  'provider_fantasy_points':{'periods':[{'period':6,'status':'provider_credited_period',
                  'leaders':[{'player_name':'Fantasy Player','team_name':'Team T','fantasy_points':5}]}]}}
    article=publish_multi_period(article_data)
    assert 'Fantasy Player' in article and '5 provider-credited fantasy points' in article
    assert 'NHL Only' not in article and 'The NHL active-roster totals differ' not in article
    article_data['provider_fantasy_points']={'periods':[]}
    article=publish_multi_period(article_data)
    assert 'Players behind the results' not in article


def test_no_fabricated_player_point_evidence(tmp_path):
    r=analyze_provider_points(tmp_path,provider='fantrax',league='league',season=2026,periods=[6,7],team_ids={'T'})
    assert r['available_periods']==[] and r['unavailable_periods']==[6,7]
