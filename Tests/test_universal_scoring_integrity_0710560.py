"""v56 universal identity sourcing, period audits, and strict scoring exceptions."""
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from Athena.Investigation.historical_roster_attribution import normalize_period_rosters, reconcile_period_points
from Athena.Investigation.standings_archive import save_snapshot
from Athena.Investigation.sync_period_scoring_audit import run, write_period_audit, audit_path
from Providers.NHL.fetch import fetch_identity_candidates


ROSTERS = {"period": 2, "rosters": {
    "t1": {"teamName": "One", "rosterItems": [
        {"id": "f1", "status": "ACTIVE", "position": "C"},
        {"id": "f2", "status": "ACTIVE", "position": "RW"},
        {"id": "f3", "status": "RESERVE", "position": "D"},
        {"id": "f4", "status": "INJURED_RESERVE", "position": "LW"}]},
    "t2": {"teamName": "Two", "rosterItems": [
        {"id": "f5", "status": "ACTIVE", "position": "C"}]},
}}


def _roster(period=2):
    return normalize_period_rosters({**ROSTERS, "period": period},
        league_id='league1', season=2026, period=period, expected_teams=2)


def _nhl(period=2, missing=False):
    # Reserve + injured skaters really scored NHL points, but not fantasy credit.
    return {"verified": True, "period": period, "roster_crosswalk_ids": ['f1','f3','f4','f5'] if missing else ['f1','f2','f3','f4','f5'],
            "records": [
                {"fantrax_player_id": "f1", "player_name":"Alpha", "goals":2,"assists":1,"points":3,"games_played":2},
                {"fantrax_player_id": "f3", "player_name":"Benched", "goals":3,"assists":3,"points":6,"games_played":2},
                {"fantrax_player_id": "f4", "player_name":"Injured", "goals":1,"assists":1,"points":2,"games_played":2},
                {"fantrax_player_id": "f5", "player_name":"Other", "goals":1,"assists":1,"points":2,"games_played":2},
            ]}


def _comparison(period=2):
    return {"status":"compared", "period":period, "teams":[
        {"team_id":"t1","name":"One","period_points":5},
        {"team_id":"t2","name":"Two","period_points":2},
    ]}


def _league():
    periods=[]
    for n, (start,end) in enumerate([
      ('2026-09-28T13:00:00-04:00','2026-10-05T18:59:59-04:00'),
      ('2026-10-05T19:00:00-04:00','2026-10-12T18:59:59-04:00'),
      ('2026-10-12T19:00:00-04:00','2026-10-19T18:59:59-04:00')],1):
      periods.append({"period":n,"startDate":start,"endDate":end})
    return {'scoringSystem':{'type':'POINTS_BASED'}, 'rosterPeriods':periods}


def _snap(root):
    for p in (1,2,3):
        save_snapshot(root,{'league_id':'league1','season':2026,'period':p,
            'source':'fixture_fantrax','timeframe':'FROM_SEASON_START','complete':True,
            'teams':[
                {'team_id':'t1','name':'One','rank':1,'points':5*(p-1)},
                {'team_id':'t2','name':'Two','rank':2,'points':2*(p-1)},
            ]})


class FakeFantrax:
    def __init__(self, **kwargs):
        pass
    def has_cookie_auth(self): return False
    def get_team_rosters(self, period): return {**ROSTERS, 'period':period}


def _window(**kwargs):
    return _nhl(kwargs['period'], missing=True)


def test_fully_explained_scoring_delta_preserves_reserves_as_excluded():
    audit = reconcile_period_points(_roster(), _nhl(missing=True), _comparison())
    t1, t2 = audit['teams']
    assert t1['difference'] == 2 and t1['status'] == 'discrepancy'
    assert t1['unmatched_active_ids'] == ['f2']
    assert t1['reserve_nhl_points_excluded'] == 8
    assert len(t1['reserve_contributors_excluded']) == 2
    assert sum(p['points'] for p in t1['contributors']) == 3
    assert t1['credited_fantasy_points_verified'] is False
    assert t1['lineup_eligibility'] == 'period_snapshot_not_game_effective'
    assert [x['type'] for x in t1['exceptions']] == ['unresolved_active_identity', 'point_difference']
    assert audit['numeric_matched_teams'] == 1
    assert audit['unmatched_active_ids'] == ['f2']
    assert audit['total_absolute_unexplained_points'] == 2
    assert audit['reserve_nhl_points_excluded'] == 8
    assert t2['numeric_match'] and t2['identity_complete']


def test_numeric_equal_with_unknown_active_identity_does_not_assert_credit():
    comparison = _comparison()
    comparison['teams'][0]['period_points'] = 3
    audit = reconcile_period_points(_roster(), _nhl(missing=True), comparison)
    assert audit['teams'][0]['status'] == 'reconciled_with_identity_gaps'
    assert not audit['teams'][0]['credited_fantasy_points_verified']
    assert audit['teams_with_identity_gaps'] == 1


def test_multi_period_sync_persists_named_exceptions_and_correct_sources(tmp_path):
    _snap(tmp_path)
    result = run(league_info=_league(), league_id='league1',season=2026,
        expected_teams=2, client_factory=FakeFantrax, nhl_acquirer=_window,
        output_dir=tmp_path, clock=datetime(2026,10,21,tzinfo=timezone.utc))
    assert result['status'] == 'partial'
    assert result['attempted_count']==2
    assert list(result['periods'])==['2','3']
    for p in (2,3):
        e = result['periods'][str(p)]
        assert e['numeric_matched_teams']==1 and e['identity_complete_teams']==1
        assert e['unmatched_active_ids']==['f2']
        assert e['point_discrepancies'][0]['difference']==2
        file = json.loads(audit_path(tmp_path,'league1',2026,p).read_text())
        assert file['teams'][0]['reserve_nhl_points_excluded']==8
        assert file['eligibility_evidence']=='period_roster_snapshot_only_not_game_effective'
    assert (tmp_path/'PeriodScoringAudit'/'sync_manifest.json').exists()


def test_audit_does_not_invent_scores_when_standings_baseline_missing(tmp_path):
    r=run(league_info=_league(),league_id='league1',season=2026,expected_teams=2,
          client_factory=FakeFantrax,nhl_acquirer=_window,output_dir=tmp_path,
          clock=datetime(2026,10,21,tzinfo=timezone.utc))
    assert r['status']=='source_unavailable' and r['attempted_count']==2
    assert all('baseline' in p['reason'].lower() for p in r['periods'].values())
    assert not audit_path(tmp_path,'league1',2026,3).exists()


def test_unverified_calendar_does_not_assert_completed_scoring(tmp_path):
    bad={'scoringSystem':{'type':'POINTS_BASED'},'rosterPeriods':[{'period':1,'startDate':'2026-10-12','endDate':'2026-10-19'}]}
    r=run(league_info=bad,league_id='league1',season=2026,expected_teams=2,
          client_factory=FakeFantrax,nhl_acquirer=_window,output_dir=tmp_path,
          clock=datetime(2026,10,21,tzinfo=timezone.utc))
    assert r['status']=='unavailable'
    assert not list((tmp_path/'PeriodScoringAudit').rglob('period_*.json'))


def test_reject_wrong_period_and_dont_mutate_audit_archive(tmp_path):
    with pytest.raises(ValueError,match='wrong-period'):
        write_period_audit(tmp_path,'league1',2026,3,{'period':2,'teams':[{}]})
    assert not audit_path(tmp_path,'league1',2026,3).exists()


def test_enriched_candidate_universe_prefers_current_year_and_preserves_sources(tmp_path):
    class NHL:
        seen=[]
        def get_skater_summary(self,season_id,game_type_id,limit):
            self.seen.append(season_id)
            year=int(season_id[:4])
            return {'total':1,'data':[{'playerId':101,'skaterFullName':'Unique Veteran',
                'teamAbbrevs':'TOR' if year==2026 else 'CGY','seasonId':int(season_id)}]}
    r=fetch_identity_candidates.run(season=2026,seasons_back=2,client_factory=NHL,
        raw_dir=tmp_path/'Raw',output_dir=tmp_path/'Output')
    assert r['status']=='verified' and r['records']==3 and r['unique_nhl_players']==1
    assert NHL.seen==['20242025','20252026','20262027']
    saved=json.loads((tmp_path/'Raw'/'nhl_identity_candidates.json').read_text())
    assert saved['source_seasons']==NHL.seen
    assert saved['schema']=='athena.nhl_identity_candidates.v2'


def test_candidate_refresh_wrong_previous_year_does_not_overwrite_existing(tmp_path):
    raw,output=tmp_path/'Raw',tmp_path/'Output';raw.mkdir();output.mkdir()
    existing=raw/'nhl_identity_candidates.json';existing.write_text('{"authoritative":true}')
    class Wrong:
        def get_skater_summary(self,season_id,game_type_id,limit):
            return {'total':1,'data':[{'playerId':101,'seasonId':20262027}]}
    status=fetch_identity_candidates.run(season=2026,seasons_back=2,client_factory=Wrong,
        raw_dir=raw,output_dir=output)
    assert status['status']=='unavailable'
    assert existing.read_text()=='{"authoritative":true}'


def test_sync_registers_general_audit_after_identity_and_previous_ingestion():
    from Athena.sync import FANTRAX_FANTASY_PIPELINE, VALIDATORS
    steps={s['id']:i for i,s in enumerate(FANTRAX_FANTASY_PIPELINE)}
    assert steps['sync_historical_period_rosters'] < steps['build_player_identity_map'] < steps['audit_historical_period_scoring']
    assert not FANTRAX_FANTASY_PIPELINE[steps['audit_historical_period_scoring']]['required']
    assert 'validate_historical_scoring_audit' in VALIDATORS


def test_nhl_name_history_can_resolve_old_alias_without_merging_distinct_ids():
    from Knowledge.player_identity_resolver import _build_nhl_candidates, _match_player, _normalize_text
    source = [{'playerId': 847001, 'skaterFullName': 'Jonathan Example', 'teamAbbrevs': 'TOR'},
              {'playerId': 847001, 'skaterFullName': 'Jon Example', 'teamAbbrevs': 'VAN'},
              {'playerId': 847002, 'skaterFullName': 'Jonathan Examples', 'teamAbbrevs': 'NYR'}]
    candidates = _build_nhl_candidates(source)
    assert len(candidates) == 2
    index = {}
    for c in candidates:
        for alias in c['normalized_aliases']:
            index.setdefault(alias, []).append(c)
    old = _match_player({'player_id':'p1','player_name':'Jonathan Example','nhl_team':'TOR'}, candidates, index)
    assert old['resolution_status']=='resolved'
    assert old['nhl_player_id']=='847001'
    assert 'jonathan example' in candidates[0]['normalized_aliases']
    assert candidates[0]['nhl_team']=='VAN'  # current affiliation independent of stable ID


def test_shared_identity_alias_collision_is_not_automatically_merged():
    from Knowledge.player_identity_resolver import _build_nhl_candidates, _match_player
    rows=[{'playerId':1,'skaterFullName':'Alex Common','teamAbbrevs':'TOR'},
          {'playerId':2,'skaterFullName':'Alex Common','teamAbbrevs':'TOR'}]
    candidates=_build_nhl_candidates(rows)
    index={}
    for c in candidates:
        for alias in c['normalized_aliases']:
            index.setdefault(alias, []).append(c)
    row=_match_player({'player_id':'f1','player_name':'Alex Common','nhl_team':'TOR'},candidates,index)
    assert row['resolution_status']=='ambiguous'
    assert row['nhl_player_id']==''


def test_historical_identity_coverage_indexes_all_periods_with_separate_status(tmp_path):
    from Knowledge.player_identity_resolver import summarize_identity_coverage
    root=tmp_path/'PeriodRosters'
    for period in (1,2,3):
        payload = _roster(period)
        p=root/'league1'/'2026'/f'period_{period:03d}.json'
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(payload))
    rows=[{'fantrax_player_id':'f1','canonical_player_name':'Alpha',
           'nhl_player_id':'101','resolution_status':'resolved'},
          {'fantrax_player_id':'f2','canonical_player_name':'Beta',
           'resolution_status':'review'}]
    report=summarize_identity_coverage(rows,current_ids={'f1','f2','f5'},archives_root=root)
    assert report['current_resolved_count']==1
    assert report['current_roster_count']==3
    assert report['historical_periods_with_gaps']==3
    for p in (1,2,3):
        entry=report['historical_periods'][f'league1/2026/{p}']
        assert entry['active_count']==3
        assert entry['active_resolved']==1
        assert len(entry['unverified_active'])==2
        assert {r['fantrax_player_id'] for r in entry['unverified_active']}=={'f2','f5'}
    assert report['current_unverified'][0]['resolution_status'] in ('review','not_in_identity_map')


def test_historical_identity_coverage_ignores_corrupted_unverified_archive(tmp_path):
    from Knowledge.player_identity_resolver import summarize_identity_coverage
    root=tmp_path/'PeriodRosters';p=root/'league1'/'2026'/'period_003.json';p.parent.mkdir(parents=True)
    p.write_text(json.dumps({**_roster(3),'records':[{'player_id':'duplicate','roster_status':'ACTIVE','active_for_period':True}]*2}))
    result=summarize_identity_coverage([],current_ids=set(),archives_root=root)
    assert result['historical_periods']=={}
    assert result['historical_periods_with_gaps']==0


def test_precise_calendar_puckdrop_window_uses_time_not_midnight():
    from Athena.Investigation.fantrax_period_calendar import resolve_unified_period
    payload={'scoringSystem':{'type':'POINTS_BASED'},'rosterPeriods':[
        {'period':1,'startDate':'2026-10-12T13:00:00-04:00','endDate':'2026-10-19T18:59:59-04:00'},
        {'period':2,'startDate':'2026-10-19T19:00:00-04:00','endDate':'2026-10-26T18:59:59-04:00'},
    ]}
    before=resolve_unified_period(payload, at=datetime(2026,10,19,22,59,58,tzinfo=timezone.utc))
    after=resolve_unified_period(payload, at=datetime(2026,10,19,23,0,0,tzinfo=timezone.utc))
    assert before['status']=='no_completed_period' and before['period'] is None
    assert after['status']=='calendar_closed' and after['period']==1
    assert resolve_unified_period(payload,at=datetime(2026,10,20))['status']=='unverified'


def test_cross_league_period_source_cannot_reconcile_by_coincidence():
    wrong=_nhl()
    wrong['league_id']='otherleague'
    assert reconcile_period_points(_roster(),wrong,_comparison())['status']=='wrong_source'
    wrong2=_comparison()
    wrong2['season']=2025
    assert reconcile_period_points(_roster(),_nhl(),wrong2)['status']=='wrong_source'


def test_revised_period_audit_preserves_previous_snapshot(tmp_path):
    first=reconcile_period_points(_roster(),_nhl(missing=True),_comparison())
    write_period_audit(tmp_path,'league1',2026,2,first)
    second=reconcile_period_points(_roster(),_nhl(missing=True),_comparison())
    second['teams'][0]['difference']=3
    write_period_audit(tmp_path,'league1',2026,2,second)
    revisions=list((audit_path(tmp_path,'league1',2026,2).parent/'revisions').glob('period_002_revision_*.json'))
    assert len(revisions)==1
    assert json.loads(revisions[0].read_text())['teams'][0]['difference']==2
    assert json.loads(audit_path(tmp_path,'league1',2026,2).read_text())['teams'][0]['difference']==3
