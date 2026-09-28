"""Validate season-scoped historical identity enrichment contracts."""
from __future__ import annotations
import json, tempfile, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from Core.version import ATHENA_VERSION, RELEASE_NAME
from Knowledge.LeagueHistory.identity import build_historical_identity_resolution, enrich_historical_draft_observations
from Knowledge.LeagueHistory.evidence_registry import discover_historical_evidence

checks=[]
def check(name, ok, detail=''):
    checks.append(bool(ok)); print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
print('Historical Identity Resolution Validation'); print('='*72)
check('version', tuple(map(int, ATHENA_VERSION.split('.'))) >= (0,6,5,0,1), ATHENA_VERSION)
check('release_name', bool(RELEASE_NAME), RELEASE_NAME)
raw={'league_info':{'teamInfo':{'t1':{'id':'t1','name':'Renamed Team'}}},'player_pool':{'rosters':{'t1':{'teamName':'Renamed Team','rosterItems':[{'id':'p1','position':'C','status':'ACTIVE'},{'id':'p2','position':'D','status':'RESERVE'}]}}},'transactions':{'table':{'rows':[{'scorer':{'scorerId':'p1','name':'Player One','posShortNames':'C,LW'}}]}}}
identity=build_historical_identity_resolution(season=2020,league_id='league',raw_payloads=raw)
team=identity['teams'][0]; players={x['provider_player_id']:x for x in identity['players']}
check('team_name_same_season', team['team_name']=='Renamed Team' and team['team_identity_status']=='resolved', team)
check('manager_not_guessed', team['manager_identity_status']=='unresolved' and team['canonical_manager_id'] is None, team['manager_identity_status'])
check('franchise_not_guessed', team['franchise_identity_status']=='unresolved', team['franchise_identity_status'])
check('player_name_from_transaction', players['p1']['canonical_player_name']=='Player One' and players['p1']['player_identity_status']=='resolved', players['p1'])
check('position_evidence_combined', players['p1']['position_resolution_status']=='resolved' and players['p1']['positions']==['C','LW'], players['p1']['positions'])
check('unnamed_player_stays_unresolved', players['p2']['player_identity_status']=='unresolved' and players['p2']['positions']==['D'], players['p2'])
canonical={'season':2020,'provider':'Fantrax','provider_league_id':'league','draft_selections':[{'provider_team_id':'t1','provider_player_id':'p1','round':1,'overall_pick':1},{'provider_team_id':'t1','provider_player_id':'missing','round':2,'overall_pick':2}]}
enriched=enrich_historical_draft_observations(canonical,identity)
check('canonical_not_mutated', 'historical_team_identity' not in canonical['draft_selections'][0], canonical['draft_selections'][0])
check('enriched_preserves_authority', enriched['observations'][0]['provider_team_id']=='t1' and enriched['observations'][0]['provider_player_id']=='p1', enriched['provenance'])
check('missing_identity_explicit', enriched['observations'][1]['historical_player_identity']['player_identity_status']=='unresolved', enriched['observations'][1]['historical_player_identity'])
print('-'*72); print('Overall status:', 'PASS' if all(checks) else 'FAIL'); raise SystemExit(0 if all(checks) else 1)
