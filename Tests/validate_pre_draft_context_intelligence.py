from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from Core.version import ATHENA_VERSION, RELEASE_NAME
from Knowledge.Intelligence.Fantasy.pre_draft_context import build_pre_draft_context
from Scout.conversation.orchestration import scout_intent_plan

fails=[]
def check(name,ok,detail=''):
 print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
 if not ok:fails.append(name)

print('Pre-Draft Context & Readiness Intelligence Validation')
print('='*64)
check('version',tuple(map(int, ATHENA_VERSION.split('.'))) >= (0,6,5,0,1),ATHENA_VERSION)
check('release',bool(RELEASE_NAME),RELEASE_NAME)
x=build_pre_draft_context()
profile=json.loads((ROOT/'Output/league_profile.json').read_text(encoding='utf-8'))
pool=json.loads((ROOT/'Output/player_pool_master.json').read_text(encoding='utf-8'))
draft=json.loads((ROOT/'Output/draft_picks.json').read_text(encoding='utf-8'))
rostered_count=sum(isinstance(row,dict) and row.get('availability_status')=='rostered' for row in pool.get('records',[]))
configured_count=len((draft.get('current_draft') or {}).get('picks') or [])
check('context_available',x.get('status') in {'available','partial'},x.get('status'))
check('current_season',x.get('season')==profile.get('season'),x.get('season'))
k=x.get('keeper_state') or {}; d=x.get('draft_capital') or {}; a=x.get('available_pool') or {}
check('roster_snapshot_evidence',k.get('rostered_players')==rostered_count and sum((k.get('rostered_by_team') or {}).values())==rostered_count,k.get('rostered_players'))
expected_slots=int(profile.get('team_count') or 0)*int(profile.get('keeper_count') or 0)
check('keeper_structure_bounded',k.get('expected_keeper_slots')==expected_slots and k.get('matches_expected_keeper_state')==(bool(expected_slots) and rostered_count==expected_slots) and k.get('keeper_selection_established') is False,k)
check('draft_board_evidence',d.get('configured_slots')==configured_count and sum((d.get('configured_slots_by_current_owner') or {}).values())==configured_count,d.get('configured_slots'))
check('draft_capital_varies',d.get('min_owned_slots') < d.get('max_owned_slots'),f"{d.get('min_owned_slots')}..{d.get('max_owned_slots')}")
check('configured_not_selection',d.get('selection_count_status')=='not_yet_determined',d.get('selection_count_status'))
check('fa_semantics_bounded','live availability guarantee' in a.get('status_semantics',''),a.get('status_semantics'))
plan=scout_intent_plan('What should I know about the JHLPAA draft going into tomorrow?','fantasy')
check('scout_route',bool(plan and plan.route=='fantasy_pre_draft_context'),getattr(plan,'route',None))
check('historical_reuse_contract','historical_context' in x and 'findings' in (x.get('historical_context') or {}),(x.get('historical_context') or {}).get('status'))
print(f"Overall status: {'PASS' if not fails else 'FAIL'}")
raise SystemExit(1 if fails else 0)
