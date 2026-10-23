"""v0.7.10.55.0: durable identities, optional NHL refresh, exact 7-point regression."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from Athena.Investigation.historical_roster_attribution import normalize_period_rosters, reconcile_period_points
from Athena.Investigation.nhl_period_production import acquire_nhl_period_production
from Knowledge import player_identity_resolver as resolver
from Providers.NHL.fetch import fetch_identity_candidates as acquire


FOUR_MISSING = [
    ('03rf5', 'Rasmus Andersson', 'CGY/VGK', 'VGK', 'D', '8478397', 4),
    ('03mm6', 'Lawson Crouse', 'UTA', 'UTA', 'RW', '8478474', 1),
    ('03c0c', 'Josh Manson', 'COL', 'COL', 'D', '8476312', 1),
    ('02wy5', 'Nikita Zadorov', 'BOS', 'BOS', 'D', '8477507', 1),
]


def _source_records():
    return [{'playerId': int(nid), 'skaterFullName': name, 'teamAbbrevs': pro,
             'positionCode': 'D' if fid != '03mm6' else 'L'}
            for fid, name, fantasy_team, pro, position, nid, score in FOUR_MISSING]


def _master_records():
    return [{'player_id': fid, 'player_name': name, 'nhl_team': club, 'position': position}
            for fid, name, club, pro, position, nid, score in FOUR_MISSING]


def _build_in_fixture(monkeypatch, tmp_path: Path, *, prior=None, master=None, nhl=None, extra=None):
    output = tmp_path/'player_identity_map.json'
    if prior is not None:
        output.write_text(json.dumps(prior))
    player = tmp_path/'player_master.json'
    player.write_text(json.dumps(master if master is not None else _master_records()))
    source = tmp_path/'nhl_skater_summary.json'
    if nhl is not None:
        source.write_text(json.dumps({'data': nhl}))
    else:
        source.write_text(json.dumps({'data': _source_records()}))
    supplemental = tmp_path/'nhl_identity_candidates.json'
    if extra is not None:
        supplemental.write_text(json.dumps({'data': extra}))
    monkeypatch.setattr(resolver, 'PLAYER_MASTER_PATH', player)
    monkeypatch.setattr(resolver, 'NHL_SKATER_SUMMARY_PATH', source)
    monkeypatch.setattr(resolver, 'NHL_IDENTITY_CANDIDATES_PATH', supplemental)
    monkeypatch.setattr(resolver, 'OUTPUT_JSON', output)
    monkeypatch.setattr(resolver, 'OUTPUT_CSV', tmp_path/'player_identity_map.csv')
    return resolver.build_player_identity_map()


def test_justin_four_missing_players_resolve_from_existing_nhl_summary(monkeypatch, tmp_path):
    # 2025-26 NHL source contains all four. Previous saved roster mapping was
    # stale: three missing entirely, Andersson blocked due to changed NHL team.
    rasmus = {'fantrax_player_id':'03rf5', 'canonical_player_name':'Rasmus Andersson',
              'nhl_player_id':'8478397','resolution_status':'review',
              'match_method':'unique_exact_name_team_mismatch'}
    rows = _build_in_fixture(monkeypatch, tmp_path, prior=[rasmus])
    found = {x['fantrax_player_id']:x for x in rows}
    assert set(found) == {x[0] for x in FOUR_MISSING}
    assert all(r['resolution_status'] == 'resolved' for r in rows)
    assert found['03rf5']['nhl_player_id'] == '8478397'
    assert found['03mm6']['nhl_player_id'] == '8478474'
    assert found['03c0c']['nhl_player_id'] == '8476312'
    assert found['02wy5']['nhl_player_id'] == '8477507'
    assert found['03rf5']['match_confidence'] >= 0.90


def test_seven_missing_active_points_reconcile_without_four_reserve_points(monkeypatch, tmp_path):
    matched = _build_in_fixture(monkeypatch, tmp_path)
    matched_ids = {r['fantrax_player_id'] for r in matched if r['resolution_status'] == 'resolved'}
    raw = {'period':3, 'rosters':{'teamJ': {'teamName':"Justin's Fighting Capybaras",
        'rosterItems':[{'id':'baseline','status':'ACTIVE','position':'C'}] +
          [{'id':fid,'status':'ACTIVE','position':position} for fid,name,club,pro,position,nid,score in FOUR_MISSING] +
          [{'id':'bench','status':'RESERVE','position':'C'}]}}}
    roster = normalize_period_rosters(raw, league_id='league1', season=2026, period=3, expected_teams=1)
    scoring = [{'fantrax_player_id':'baseline','player_name':'Known contributors','points':23,'goals':11,'assists':12,'games_played':4}]
    scoring.extend({'fantrax_player_id':fid,'player_name':name,'points':points,'goals':points,'assists':0,'games_played':3}
                   for fid,name,club,pro,position,nid,points in FOUR_MISSING)
    scoring.append({'fantrax_player_id':'bench','player_name':'Reserve scorer','points':4,'goals':4,'assists':0,'games_played':3})
    nhl = {'verified':True,'period':3,'records':scoring,
           'roster_crosswalk_ids':list(matched_ids | {'baseline','bench'})}
    comparison = {'status':'compared','period':3,'teams':[{'team_id':'teamJ',
                  'name':"Justin's Fighting Capybaras",'period_points':30}]}
    audit = reconcile_period_points(roster, nhl, comparison)
    assert audit['fully_reconciled_teams'] == 1
    assert audit['teams'][0]['identified_active_nhl_points'] == 30
    assert audit['teams'][0]['difference'] == 0
    assert not any(x['name'] == 'Reserve scorer' for x in audit['teams'][0]['contributors'])


def test_identity_preserved_across_roster_change_and_unavailable_new_season(monkeypatch, tmp_path):
    old = {'fantrax_player_id':'p1','canonical_player_name':'Player Example',
           'nhl_player_id':'8475000','nhl_player_name':'Player Example',
           'resolution_status':'resolved','match_confidence':0.99,'nhl_team':'TOR'}
    historical = {'fantrax_player_id':'old_player','canonical_player_name':'Historical Player',
                  'nhl_player_id':'8476000','nhl_player_name':'Historical Player',
                  'resolution_status':'resolved','match_confidence':0.99,'nhl_team':'NYR'}
    rows = _build_in_fixture(monkeypatch, tmp_path, prior=[old,historical],
       master=[{'player_id':'p1','player_name':'Player Example','nhl_team':'VAN','position':'C'}], nhl=[])
    found = {x['fantrax_player_id']:x for x in rows}
    assert found['p1']['nhl_player_id'] == '8475000'
    assert found['p1']['resolution_status'] == 'resolved'
    assert found['old_player']['nhl_player_id'] == '8476000'
    assert found['old_player']['match_method'] == 'preserved_historical_identity'


def test_prior_verification_never_overrides_conflicting_new_candidate(monkeypatch,tmp_path):
    old = {'fantrax_player_id':'p1','canonical_player_name':'Example Skater',
           'nhl_player_id':'1111111','resolution_status':'resolved','match_confidence':0.99}
    rows = _build_in_fixture(monkeypatch,tmp_path,prior=[old],
       master=[{'player_id':'p1','player_name':'Example Skater','nhl_team':'TOR','position':'C'}],
       nhl=[{'playerId':2222222,'skaterFullName':'Example Skater','teamAbbrevs':'TOR','positionCode':'C'}])
    assert rows[0]['resolution_status'] == 'ambiguous'
    assert not rows[0]['nhl_player_id']


def test_same_nhl_identity_cannot_be_attributed_to_two_fantrax_ids(monkeypatch,tmp_path):
    rows = _build_in_fixture(monkeypatch,tmp_path,
      master=[{'player_id':'p1','player_name':'Example Skater','nhl_team':'TOR','position':'C'},
              {'player_id':'p2','player_name':'Example Skater','nhl_team':'TOR','position':'C'}],
      nhl=[{'playerId':2222222,'skaterFullName':'Example Skater','teamAbbrevs':'TOR','positionCode':'C'}])
    assert all(r['resolution_status'] == 'ambiguous' for r in rows)
    assert not any(r['nhl_player_id'] for r in rows)


def test_ambiguous_full_names_do_not_auto_resolve(monkeypatch,tmp_path):
    rows = _build_in_fixture(monkeypatch,tmp_path,
       master=[{'player_id':'p1','player_name':'Elias Pettersson','nhl_team':'VAN','position':'C'}],
       nhl=[{'playerId':111,'skaterFullName':'Elias Pettersson','teamAbbrevs':'VAN','positionCode':'C'},
            {'playerId':222,'skaterFullName':'Elias Pettersson','teamAbbrevs':'VAN','positionCode':'C'}])
    assert rows[0]['resolution_status'] == 'ambiguous'


def test_new_current_season_candidate_expands_without_duplicates(monkeypatch,tmp_path):
    rows = _build_in_fixture(monkeypatch,tmp_path,
       master=[{'player_id':'p1','player_name':'Old Star','nhl_team':'TOR','position':'C'},
               {'player_id':'p2','player_name':'New Rookie','nhl_team':'TOR','position':'LW'}],
       nhl=[{'playerId':111,'skaterFullName':'Old Star','teamAbbrevs':'NYR','positionCode':'C'}],
       extra=[{'playerId':111,'skaterFullName':'Old Star','teamAbbrevs':'TOR','positionCode':'C'},
              {'playerId':222,'skaterFullName':'New Rookie','teamAbbrevs':'TOR','positionCode':'L'}])
    assert {r['nhl_player_id'] for r in rows} == {'111','222'}
    assert all(r['resolution_status'] == 'resolved' for r in rows)


def test_reject_bad_master_id_or_empty_sources(monkeypatch,tmp_path):
    with pytest.raises(ValueError,match='duplicate'):
        _build_in_fixture(monkeypatch,tmp_path,master=[_master_records()[0]]*2)


def test_fetch_current_nhl_candidates_preserves_existing_on_failure(tmp_path):
    raw, output = tmp_path/'Raw',tmp_path/'Output'
    raw.mkdir();output.mkdir()
    class GoodClient:
        def get_skater_summary(self, season_id, game_type_id, limit):
            assert season_id == '20262027' and game_type_id == 2
            return {'total':1,'data':[{'playerId':8478397,'skaterFullName':'Rasmus Andersson','seasonId':20262027}]}
    first = acquire.run(season='2026',client_factory=GoodClient,raw_dir=raw,output_dir=output)
    assert first['status']=='verified' and first['records']==1
    original = (raw/'nhl_identity_candidates.json').read_bytes()
    class BadClient:
        def get_skater_summary(self,*args,**kwargs):
            raise ConnectionError('network unavailable')
    second = acquire.run(season='2026',client_factory=BadClient,raw_dir=raw,output_dir=output)
    assert second['status']=='unavailable'
    assert (raw/'nhl_identity_candidates.json').read_bytes()==original


def test_fetch_rejects_incomplete_and_wrong_season(tmp_path):
    class InvalidClient:
        def get_skater_summary(self,*a,**kw):
            return {'total':2,'data':[{'playerId':777,'seasonId':20252026}]}
    result = acquire.run(season='2026',client_factory=InvalidClient,
                         raw_dir=tmp_path/'Raw',output_dir=tmp_path/'Output')
    assert result['status']=='unavailable'
    assert not (tmp_path/'Raw'/'nhl_identity_candidates.json').exists()


def test_sync_pipeline_rebuilds_identity_after_player_master():
    from Athena.sync import FANTRAX_FANTASY_PIPELINE, VALIDATORS
    steps = {step['id']:i for i,step in enumerate(FANTRAX_FANTASY_PIPELINE)}
    assert steps['build_player_master'] < steps['fetch_nhl_identity_candidates'] < steps['build_player_identity_map']
    assert not FANTRAX_FANTASY_PIPELINE[steps['fetch_nhl_identity_candidates']]['required']
    assert FANTRAX_FANTASY_PIPELINE[steps['build_player_identity_map']]['script'] == 'Knowledge/player_identity_resolver.py'
    assert 'validate_player_identity_map' in VALIDATORS


def test_fantasy_nhl_window_cache_invalidates_when_identity_map_changes(tmp_path):
    from Tests.test_points_based_player_reporting_0710530 import _data, _schedule, _params
    class NHL:
        calls=[]
        def get_stats(self, endpoint, params):
            NHL.calls.append('stats')
            return _data()
        def get_web(self, endpoint):
            return _schedule()[0]
    root=tmp_path
    identity=_params()['identity_rows'][:1]
    (root/'player_identity_map.json').write_text(json.dumps(identity))
    (root/'player_master.json').write_text(json.dumps(_params()['roster_rows']))
    boundary={'status':'verified_boundary','boundary_kind':'points_based_roster_period',
              'start_at':_params()['start_at'],'end_at':_params()['end_at']}
    base=dict(league_id='league1',season=2026,period=3,boundary=boundary,
              client_factory=NHL,output_dir=root,clock=datetime(2026,10,21,tzinfo=timezone.utc))
    first=acquire_nhl_period_production(**base)
    assert first['verified'] and first['roster_crosswalk_resolved']==1
    assert acquire_nhl_period_production(**base).get('cached') is True
    (root/'player_identity_map.json').write_text(json.dumps(_params()['identity_rows']))
    second=acquire_nhl_period_production(**base)
    assert second['verified'] and second['roster_crosswalk_resolved']==2
    assert not second.get('cached')
    assert NHL.calls==['stats','stats']
