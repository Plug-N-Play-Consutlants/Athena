"""Validate evidence-backed historical draft intelligence contracts."""
from __future__ import annotations
import json, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from Core.version import ATHENA_VERSION, RELEASE_NAME
from Knowledge.Intelligence.Fantasy.historical_draft import build_historical_draft_intelligence

checks=[]
def check(name, ok, detail=''):
    checks.append(bool(ok)); print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")

print('Historical Draft Intelligence Validation'); print('='*72)
check('version', tuple(map(int, ATHENA_VERSION.split('.'))) >= (0,6,5,0,1), ATHENA_VERSION)
check('release_name', bool(RELEASE_NAME), RELEASE_NAME)
with tempfile.TemporaryDirectory() as td:
    root=Path(td)
    for season in range(2016,2026):
        sd=root/'Output'/'Historical'/str(season); sd.mkdir(parents=True)
        obs=[]
        # 12 resolved round-1 forwards and 12 resolved round-7 defensemen per season.
        for i in range(12):
            obs.append({'season':season,'round':1,'provider_team_id':f't{i%3}','provider_player_id':f'f{i}',
                'historical_team_identity':{'team_name':f'Team {i%3}','team_identity_status':'resolved'},
                'historical_player_identity':{'positions':['C'],'position_resolution_status':'resolved','player_identity_status':'unresolved'}})
            obs.append({'season':season,'round':7,'provider_team_id':f't{i%3}','provider_player_id':f'd{i}',
                'historical_team_identity':{'team_name':f'Team {i%3}','team_identity_status':'resolved'},
                'historical_player_identity':{'positions':['D'],'position_resolution_status':'resolved','player_identity_status':'unresolved'}})
        (sd/'draft_observations_enriched.json').write_text(json.dumps({'season':season,'observations':obs}),encoding='utf-8')
    intel=build_historical_draft_intelligence(project_root=root)
    check('ten_seasons', intel['season_count']==10, intel['season_count'])
    check('position_coverage', intel['coverage']['position_coverage_pct']==100.0, intel['coverage'])
    findings={x['type']:x for x in intel['findings']}
    check('round_depth_pattern', findings.get('round_depth_position_pattern',{}).get('status')=='supported', findings.get('round_depth_position_pattern'))
    check('era_mix_not_invented', findings.get('era_position_mix',{}).get('status')=='stable', findings.get('era_position_mix'))
    check('no_manager_attribution', intel['attribution_policy']['cross_season_team_or_manager_tendencies_allowed'] is False, intel['attribution_policy'])
    check('same_season_team_profiles_allowed', intel['attribution_policy']['same_season_team_profiles_allowed'] is True, intel['attribution_policy'])
    check('source_files_declared', len(intel['files_read'])==10, intel['files_read'])
print('-'*72); print('Overall status:', 'PASS' if all(checks) else 'FAIL'); raise SystemExit(0 if all(checks) else 1)
