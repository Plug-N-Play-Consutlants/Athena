from __future__ import annotations
import json, tempfile, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Core.version import ATHENA_VERSION, RELEASE_NAME
from Core.text_utils import normalize_external_text
from Knowledge.Intelligence.Fantasy.pre_draft_context import build_pre_draft_context
from Scout.conversation.context import load_context
from Scout.conversation.router import analyze_league
from Scout.conversation.orchestration import _answer_pre_draft_branch

fail=[]
def check(name, ok, detail=''):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    if not ok: fail.append(name)

check('version_at_least_0_6_5_0_4', tuple(map(int, ATHENA_VERSION.split('.'))) >= (0,6,5,0,4), ATHENA_VERSION)
check('release_name_available', bool(RELEASE_NAME.strip()), RELEASE_NAME)
check('mojibake_normalization', normalize_external_text('Bubbaâ€™s Bruisers')=='Bubba’s Bruisers', normalize_external_text('Bubbaâ€™s Bruisers'))

ctx=load_context(); league=analyze_league(ctx)
cards={c.get('label'):c.get('value') for c in league.get('cards',[]) if isinstance(c,dict)}
check('no_active_member_mislabel', 'Managers active' not in cards, cards)
check('observed_move_terminology', 'Managers with observed moves' in cards, cards)
check('roster_contract_draft_cards', all(k in cards for k in ['Rostered keepers','Contracts','Current draft slots','Future draft assets','Historical drafts']), cards)

with tempfile.TemporaryDirectory() as td:
    root=Path(td); (root/'Output').mkdir(); (root/'Raw').mkdir()
    (root/'Output/league_profile.json').write_text(json.dumps({'season':2026,'team_count':2,'keeper_count':1,'scoring_model':'points','league_subtype':'contract_dynasty'}))
    (root/'Output/draft_picks.json').write_text(json.dumps({'current_draft':{'round_count':1,'picks':[{'current_owner':{'team_name':'A'}},{'current_owner':{'team_name':'B'}}]}}))
    (root/'Output/player_pool_master.json').write_text(json.dumps({'records':[{'availability_status':'rostered','fantasy_team':'A','position':'C'},{'availability_status':'rostered','fantasy_team':'B','position':'D'}]}))
    (root/'Raw/Fantrax-Players-JHLPAA.csv').write_text('ID,Player,Status,RkOv,Position\n1,Snapshot Star,FA,1,C\n2,Other,FA,2,D\n', encoding='utf-8')
    intel=build_pre_draft_context(project_root=root); avail=intel['available_pool']
    check('snapshot_semantics_bounded', avail['snapshot_fa_rows']==2 and not avail['live_availability_observed'], avail)
    check('snapshot_not_promoted', 'top_source_ranked' not in avail, avail)

ans=_answer_pre_draft_branch(ctx,'What does the current keeper state imply about the available player pool?','fantasy_keeper_pool_context')
blob=json.dumps(ans,ensure_ascii=False)
check('no_snapshot_best_available', 'Highest source-ranked FA-marked examples' not in blob, ans.get('observed_facts'))
check('availability_authority_explicit', 'snapshot' in blob.lower() and ('live availability' in blob.lower() or 'live available' in blob.lower()), ans.get('natural_language_response'))
print('Overall status:', 'PASS' if not fail else 'FAIL')
raise SystemExit(1 if fail else 0)
