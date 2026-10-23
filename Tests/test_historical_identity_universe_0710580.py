"""v0.7.10.58.0: historical identity universe, evidence conflicts and audit diagnoses."""
from __future__ import annotations

import json
from pathlib import Path

from Athena.Investigation.historical_roster_attribution import normalize_period_rosters
from Athena.Investigation.multi_period_audit import investigate_requested_periods
from Athena.Investigation.sync_period_scoring_audit import audit_path
from Knowledge import player_identity_resolver as resolver


def _source():
    return [
        {'playerId':8480012,'skaterFullName':'Elias Pettersson', 'teamAbbrevs':'VAN','positionCode':'C'},
        {'playerId':8483678,'skaterFullName':'Elias Pettersson', 'teamAbbrevs':'VAN','positionCode':'D'},
        {'playerId':8480015,'skaterFullName':'Owen Tippett', 'teamAbbrevs':'PHI','positionCode':'R'},
        {'playerId':8482159,'skaterFullName':'Tyson Foerster', 'teamAbbrevs':'PHI','positionCode':'R'},
        {'playerId':8478975,'skaterFullName':'Mason Marchment', 'teamAbbrevs':'CBJ','positionCode':'L'},
    ]


def _setup(monkeypatch, tmp_path, *, previous=None, transaction=None, current=None, nhl=None, archive=True):
    raw = tmp_path/'Raw'; output=tmp_path/'Output';raw.mkdir();output.mkdir()
    (raw/'nhl_skater_summary.json').write_text(json.dumps({'data':_source() if nhl is None else nhl}))
    (raw/'transactions.json').write_text(json.dumps(transaction if transaction is not None else
         {'table':{'rows':[
           {'scorer':{'scorerId':'03yh8','name':'Owen Tippett','posShortNames':'RW'}},
           {'scorer':{'scorerId':'05k8c','name':'Tyson Foerster','posShortNames':'LW'}},
           {'scorer':{'scorerId':'03wor','name':'Mason Marchment','posShortNames':'LW'}},
         ]}}))
    (output/'player_master.json').write_text(json.dumps(current if current is not None else [
        {'player_id':'048x9','player_name':'Elias Pettersson','nhl_team':'VAN','position':'C'}]))
    if previous is None:
        previous = [{'fantrax_player_id':'03wor','canonical_player_name':'Mason Marchment',
                     'fantrax_nhl_team':'SEA/CBJ','fantrax_position':'LW',
                     'nhl_player_id':'8478975','nhl_player_name':'Mason Marchment',
                     'resolution_status':'review','match_confidence':0.86}]
    (output/'player_identity_map.json').write_text(json.dumps(previous))
    if archive:
        for period in (2,3):
            payload = normalize_period_rosters({'period':period, 'rosters':{'t1':{
                'teamName':'Historical Test', 'rosterItems':[
                    {'id':'048x9','status':'ACTIVE','position':'C'},
                    {'id':'03yh8','status':'ACTIVE','position':'RW'},
                    {'id':'05k8c','status':'ACTIVE','position':'LW'},
                    {'id':'03wor','status':'ACTIVE','position':'LW'},
                ]}}}, league_id='league1',season=2026,period=period,expected_teams=1)
            path=output/'PeriodRosters'/'league1'/'2026'/f'period_{period:03d}.json'
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(payload))
    for key, val in [('PLAYER_MASTER_PATH',output/'player_master.json'),
                     ('NHL_SKATER_SUMMARY_PATH',raw/'nhl_skater_summary.json'),
                     ('NHL_IDENTITY_CANDIDATES_PATH',raw/'missing_nhl_candidates.json'),
                     ('OUTPUT_JSON',output/'player_identity_map.json'),
                     ('OUTPUT_CSV',output/'player_identity_map.csv')]:
        monkeypatch.setattr(resolver,key,val)
    return output, raw


def test_all_four_historical_ids_reconcile_through_shared_resolver(monkeypatch,tmp_path):
    output,_=_setup(monkeypatch,tmp_path)
    matched=resolver.build_player_identity_map()
    found={x['fantrax_player_id']:x for x in matched}
    assert {fid:found[fid]['nhl_player_id'] for fid in ('048x9','03yh8','05k8c','03wor')} == {
        '048x9':'8480012','03yh8':'8480015','05k8c':'8482159','03wor':'8478975'}
    assert all(found[fid]['resolution_status']=='resolved' for fid in found)
    assert found['048x9']['match_method']=='exact_name_unique_position'
    assert 'fantrax_transaction_scorer' in found['03yh8']['identity_sources']
    assert 'prior_identity_registry' in found['03wor']['identity_sources']
    assert found['03yh8']['historical_identity'] is True
    coverage=json.loads((output/'player_identity_coverage.json').read_text())
    assert coverage['historical_periods_with_gaps']==0
    assert all(x['active_resolved']==4 for x in coverage['historical_periods'].values())
    # Subsequent syncs do not lose historical entries after the transactions
    # archive ages out or an NHL source fails to include the historic skater.
    (tmp_path/'Raw'/'transactions.json').write_text('{}')
    (tmp_path/'Raw'/'nhl_skater_summary.json').write_text('{"data":[]}')
    again={x['fantrax_player_id']:x for x in resolver.build_player_identity_map()}
    assert all(again[fid]['resolution_status']=='resolved' for fid in found)


def test_historical_roster_without_provider_name_stays_unresolved(monkeypatch,tmp_path):
    output,raw=_setup(monkeypatch,tmp_path,previous=[],transaction={},archive=True)
    rows={r['fantrax_player_id']:r for r in resolver.build_player_identity_map()}
    for fid in ('03yh8','05k8c','03wor'):
        assert rows[fid]['resolution_status']=='unresolved'
        assert rows[fid]['match_method']=='missing_historical_fantrax_name'
        assert rows[fid]['nhl_player_id']==''
    report=json.loads((output/'player_identity_coverage.json').read_text())
    assert report['historical_periods_with_gaps']==2
    assert all(len(p['unverified_active'])==3 for p in report['historical_periods'].values())


def test_conflicting_historical_names_block_auto_assignment(monkeypatch,tmp_path):
    output,raw=_setup(monkeypatch,tmp_path,archive=False,previous=[
        {'fantrax_player_id':'03yh8','canonical_player_name':'Different Player',
         'resolution_status':'review'}])
    found={r['fantrax_player_id']:r for r in resolver.build_player_identity_map()}
    assert found['03yh8']['resolution_status']=='ambiguous'
    assert found['03yh8']['match_method']=='conflicting_fantrax_identity_names'
    assert not found['03yh8']['nhl_player_id']


def test_current_fantrax_id_changed_name_requires_same_nhl_id(monkeypatch,tmp_path):
    output,raw=_setup(monkeypatch,tmp_path,archive=False,transaction={},current=[
        {'player_id':'p1','player_name':'Owen Tippett','nhl_team':'PHI','position':'RW'}],previous=[
        {'fantrax_player_id':'p1','canonical_player_name':'Mason Marchment',
         'nhl_player_id':'8478975','resolution_status':'resolved','match_confidence':0.99}])
    rows=resolver.build_player_identity_map()
    p1=next(x for x in rows if x['fantrax_player_id']=='p1')
    assert p1['resolution_status']=='ambiguous'
    assert p1['match_method']=='fantrax_id_name_conflict'
    assert p1['nhl_player_id']==''


def test_same_name_with_unique_position_is_not_same_name_same_position(monkeypatch,tmp_path):
    output,raw=_setup(monkeypatch,tmp_path,archive=False,transaction={},current=[
        {'player_id':'p1','player_name':'Elias Pettersson','nhl_team':'VAN','position':'D'},
        {'player_id':'p2','player_name':'Owen Tippett','nhl_team':'PHI','position':'RW'}])
    rows={x['fantrax_player_id']:x for x in resolver.build_player_identity_map()}
    assert rows['p1']['nhl_player_id']=='8483678'
    assert rows['p2']['nhl_player_id']=='8480015'
    # Two NHL entries with identical name, team and position are ambiguous.
    (raw/'nhl_skater_summary.json').write_text(json.dumps({'data':[
        {'playerId':11,'skaterFullName':'Elias Pettersson','teamAbbrevs':'VAN','positionCode':'D'},
        {'playerId':22,'skaterFullName':'Elias Pettersson','teamAbbrevs':'VAN','positionCode':'D'}]}))
    second={x['fantrax_player_id']:x for x in resolver.build_player_identity_map()}
    assert second['p1']['resolution_status']=='ambiguous'
    assert second['p1']['nhl_player_id']==''


def test_bad_archive_cannot_inject_an_identity(monkeypatch,tmp_path):
    output,raw=_setup(monkeypatch,tmp_path,previous=[],transaction={},archive=False)
    archive=output/'PeriodRosters'/'league1'/'2026'/'period_003.json'
    archive.parent.mkdir(parents=True,exist_ok=True)
    roster=normalize_period_rosters({'period':3,'rosters':{'t1':{
        'teamName':'Test','rosterItems':[{'id':'fake01','status':'ACTIVE','position':'C'}]}}},
        league_id='league1',season=2026,period=3,expected_teams=1)
    roster['player_count']=100  # corrupt claimed count
    archive.write_text(json.dumps(roster))
    rows={x['fantrax_player_id']:x for x in resolver.build_player_identity_map()}
    assert 'fake01' not in rows


def test_multi_period_audit_exposes_names_and_reasons_without_changing_points(tmp_path):
    (tmp_path/'player_identity_map.json').write_text(json.dumps([
        {'fantrax_player_id':'048x9','canonical_player_name':'Elias Pettersson',
         'resolution_status':'review','match_method':'exact_name_and_position_ambiguous_team',
         'fantrax_position':'C'}]))
    path=audit_path(tmp_path,'league1',2026,3);path.parent.mkdir(parents=True,exist_ok=True)
    archive={'schema':'athena.period_attribution.v1','league_id':'league1','season':'2026',
       'period':3,'numeric_matched_teams':0,'fully_reconciled_teams':0,
       'unmatched_active_ids':['048x9'],'reserve_nhl_points_excluded':7,
       'teams':[{'team_id':'t1','team_name':'Waterbury','status':'discrepancy','difference':2,
                 'fantrax_points':38,'identified_active_nhl_points':36,
                 'unmatched_active_ids':['048x9'],'reserve_nhl_points_excluded':7}]}
    path.write_text(json.dumps(archive))
    def runner(**kwargs):
        return {'periods':{'3':{'status':'partial','team_count':1}}}
    outcome=investigate_requested_periods(output_dir=tmp_path,league_id='league1',season=2026,
             periods=[3],expected_teams=1,runner=runner)
    team=outcome['periods'][0]['teams'][0]
    assert team['unmatched_active_details'][0]['player_name']=='Elias Pettersson'
    assert team['unmatched_active_details'][0]['match_method']=='exact_name_and_position_ambiguous_team'
    assert team['difference']==2
    assert outcome['periods'][0]['reserve_nhl_points_excluded']==7
