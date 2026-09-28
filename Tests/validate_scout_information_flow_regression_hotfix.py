from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from Core.version import ATHENA_VERSION, RELEASE_NAME
from Scout.conversation.orchestration import scout_intent_plan
from Scout.conversation.router import route_question

def check(name, ok, detail=''):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    return bool(ok)

def main():
    rows=[]
    app=(ROOT/'Scout/app.py').read_text(encoding='utf-8')
    rows.append(check('version',tuple(map(int, ATHENA_VERSION.split('.'))) >= (0,6,5,0,1),ATHENA_VERSION))
    rows.append(check('release_name',bool(RELEASE_NAME),RELEASE_NAME))
    rows.append(check('news_card_css','.source-item {' in app and '.source-headline {' in app,'structured evidence card styling'))
    rows.append(check('more_results_collapsed','.more-results-body[hidden] { display:none; }' in app and 'toggleMoreResults' in app,'collapsed More Results contract'))
    rows.append(check('investigate_further_styled',"content:'Investigate Further'" in app and 'suggested-prompt' in app,'prompt presentation contract'))
    rows.append(check('session_full_record','record = dict(answer)' in app and 'Primary evidence' in app and 'Live evidence diagnostics' in app,'11.1 observability preserved'))
    bare=scout_intent_plan('Gavin McKenna','public')
    rows.append(check('bare_mckenna_not_hypothetical',bare is None or bare.route!='public_organization_impact',None if bare is None else bare.route))
    explicit=scout_intent_plan("The Toronto Maple Leafs selected Gavin McKenna first overall in the 2026 NHL Draft. Evaluate how that decision changes the organization's outlook over the next five years.",'public')
    rows.append(check('explicit_mckenna_scenario',explicit is not None and explicit.route=='public_organization_impact',None if explicit is None else explicit.route))
    m=route_question('Gavin McKenna',mode='public')
    rows.append(check('bare_mckenna_public_prospect_context',m.get('intent')=='public_player_profile',f"{m.get('intent')} | {m.get('title')}"))
    a=route_question('Auston Matthews',mode='public')
    rows.append(check('matthews_rich_profile_preserved',a.get('intent')=='public_player_profile',f"{a.get('intent')} | {a.get('title')}"))
    print(f"\nOverall status: {'PASS' if all(rows) else 'FAIL'}")
    return 0 if all(rows) else 1
if __name__=='__main__': raise SystemExit(main())
