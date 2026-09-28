"""Validate historical draft normalization and multi-season ingestion contracts."""
from __future__ import annotations
import inspect
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from Core.version import ATHENA_VERSION, RELEASE_NAME
from Knowledge.LeagueHistory.draft_results import normalize_historical_draft_results
import Tools.acquire_historical_league as acquisition

checks=[]
def check(name, ok, detail=''):
    checks.append(bool(ok)); print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")

print('Historical Draft Ingestion Validation')
print('='*72)
registry=json.loads((ROOT/'Configuration/historical_leagues.json').read_text(encoding='utf-8'))
entries=registry.get('historical_leagues',[])
check('version_0_6_4_6_0', ATHENA_VERSION=='0.6.4.6.0', ATHENA_VERSION)
check('release_name', RELEASE_NAME=='Historical League Draft Ingestion Foundation', RELEASE_NAME)
check('registered_history_through_2016', min(int(x['season']) for x in entries)==2016, [x['season'] for x in entries])
check('all_registered_ids_nonempty', all(str(x.get('league_id','')).strip() for x in entries), len(entries))
fixture={'draftState':'completed','draftType':'snake','draftOrder':['t1','t2'],'draftPicks':[
    {'round':1,'pick':1,'pickInRound':1,'teamId':'t1','playerId':'p1','time':1000},
    {'round':1,'pick':2,'pickInRound':2,'teamId':'t2','time':2000},
]}
canon=normalize_historical_draft_results(fixture,season=2025,league_id='league')
check('all_slots_preserved', canon['configured_slot_count']==2 and len(canon['draft_slots'])==2, canon['configured_slot_count'])
check('only_playerid_is_selection', canon['selection_count']==1 and len(canon['draft_selections'])==1, canon['selection_count'])
check('empty_slot_not_reconstructed', canon['draft_slots'][1]['slot_status']=='no_player_selection' and canon['draft_slots'][1]['provider_player_id'] is None, canon['draft_slots'][1])
check('provider_ids_preserved', canon['draft_selections'][0]['provider_team_id']=='t1' and canon['draft_selections'][0]['provider_player_id']=='p1', canon['draft_selections'][0])
check('identity_resolution_deferred', 'same_season' in canon['identity_resolution']['team_identity'], canon['identity_resolution'])
check('read_only', canon['active_workspace_mutation_allowed'] is False, canon['scope'])
source=inspect.getsource(acquisition)
check('bulk_acquisition_contract', 'def acquire_all()' in source and 'load_historical_registry()' in source, 'registered seasons drive sweep')
check('canonical_artifact_written', 'draft_results_canonical.json' in source, 'Output/Historical/<season>')
check('compact_sweep_artifact', 'acquisition_sweep.json' in source, 'Output/Historical/acquisition_sweep.json')
check('no_active_workspace_mutation', 'workspace.json' not in source, 'historical isolation')
print('-'*72); print('Overall status:', 'PASS' if all(checks) else 'FAIL')
raise SystemExit(0 if all(checks) else 1)
