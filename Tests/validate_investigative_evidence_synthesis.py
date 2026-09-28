from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from Core.version import ATHENA_VERSION
from Scout.conversation.router import _focused_live_events, _evidence_synthesis_narrative, _synthesis_followup_prompts
fails=[]
def check(n,o,d=''):
 print(f"[{'PASS' if o else 'FAIL'}] {n}: {d}"); fails.append(n) if not o else None
print('Investigative Evidence Synthesis Validation'); print('='*64)
events=[
 {'title':'Time and Space: Maple Leafs coach Jim Hiller emphasizes creative entries and pace','summary':'Toronto is changing entries and pace.'},
 {'title':"Does Matthew Knies' Play Style Suit Jim Hiller's Maple Leafs System?",'summary':'Knies fit in the new system.'},
 {'title':"Can Maple Leafs Morgan Rielly thrive in different role?",'summary':'Rielly role change.'},
 {'title':'Maple Leafs Sign Defenceman Nick Blankenburg','summary':'Toronto signing.'},
]
q="What is changing in the team's system and player roles, and what evidence supports it? in recent Toronto Maple Leafs news?"
focused,mode=_focused_live_events(q,events)
check('version',tuple(map(int,ATHENA_VERSION.split('.'))) >= (0,6,5,10,6),ATHENA_VERSION)
check('system_followup_routes_to_synthesis',mode=='evidence_synthesis:system_roles',mode)
check('system_evidence_is_focused',len(focused)==3,[e['title'] for e in focused])
natural=_evidence_synthesis_narrative(q,focused,mode)
check('synthesis_answers_question','creative entries and pace' in natural and 'Rielly' in natural,natural)
prompts=_synthesis_followup_prompts(mode)
check('synthesis_deepens_investigation',len(prompts)==2,prompts)
check('selected_prompt_not_regenerated',all('What is changing in the team' not in p for p in prompts),prompts)
broad, broad_mode=_focused_live_events('Maple Leafs news',events)
check('broad_news_remains_discovery',broad_mode=='broad_discovery',broad_mode)
print(f"Overall status: {'PASS' if not fails else 'FAIL'}"); raise SystemExit(1 if fails else 0)
