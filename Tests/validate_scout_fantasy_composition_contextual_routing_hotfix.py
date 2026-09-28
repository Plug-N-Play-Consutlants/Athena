import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Core.version import ATHENA_VERSION, RELEASE_NAME
from Scout.conversation.context import load_context
from Scout.conversation.orchestration import scout_intent_plan, scout_orchestrated_answer
from Scout.conversation.router import analyze_league
from Knowledge.knowledge_readiness import _source_path_for_key

checks=[]
def check(name, ok, detail=''):
    checks.append(bool(ok)); print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")

check('version', tuple(map(int, ATHENA_VERSION.split('.'))) >= (0,6,5,0,3), ATHENA_VERSION)
check('release', bool(RELEASE_NAME), RELEASE_NAME)
ctx=load_context()
branches={
 'What does the current keeper state imply about the available player pool?':'fantasy_keeper_pool_context',
 'How uneven is current draft capital across the league?':'fantasy_draft_capital_context',
 'Where does the draft historically change character by round?':'fantasy_historical_draft_context',
 'Which historical draft patterns are most relevant to tomorrow\'s draft?':'fantasy_historical_draft_context',
}
for prompt, expected in branches.items():
    plan=scout_intent_plan(prompt,'fantasy')
    check('route_'+expected, bool(plan and plan.route==expected), getattr(plan,'route',None))
    ans=scout_orchestrated_answer(ctx,prompt,'fantasy')
    check('execute_'+expected, bool(ans and ans.get('intent')==expected and ans.get('title')!='Scout needs one more detail'), (ans or {}).get('title'))
    check('normal_detail_'+expected, bool(ans and ans.get('normal_detail')), (ans or {}).get('normal_detail'))
league=analyze_league(ctx)
check('league_normal_detail', league.get('normal_detail') is True, league.get('normal_detail'))
check('league_followups', len(league.get('suggested_prompts') or [])>=3, league.get('suggested_prompts'))
path=_source_path_for_key('draft_picks')
check('draft_readiness_uses_canonical_output', path is not None and str(path).replace('\\','/').endswith('Output/draft_picks.json'), path)
raise SystemExit(0 if all(checks) else 1)
