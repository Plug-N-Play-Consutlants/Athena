from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from Core.version import ATHENA_VERSION
from Knowledge.Events.live_intelligence import _event_matches_filters, _select_story_diversity
p=Path('Knowledge/Events/live_intelligence.py'); text=p.read_text(encoding='utf-8')
fails=[]
def check(n,o,d=''):
 print(f"[{'PASS' if o else 'FAIL'}] {n}: {d}"); fails.append(n) if not o else None
print('Public Team News Relevance Validation'); print('='*64)
check('version',tuple(map(int, ATHENA_VERSION.split('.'))) >= (0,6,5,0,1),ATHENA_VERSION)
e={'title':"Oilers' Hyman discusses Babcock",'summary':'Edmonton forward comments on the Oilers coach.','event_type':'event'}
ok,reasons=_event_matches_filters(e,{'leafs','maple','toronto'},set())
check('unrelated_team_rejected',not ok,reasons)
check('entity_mismatch_preserved','entity_mismatch' in reasons,reasons)
check('linked_article_centrality_contract','opening_mentions >= 2' in text and 'heading_match' in text,'heading/opening centrality required')
check('no_anywhere_body_match','return bool(phrase and phrase in text)' not in text,'passing mention no longer sufficient')

items=[
 {'title':'Why the Maple Leafs placed Steven Lorentz on waivers','summary':'Steven Lorentz was placed on waivers by Toronto.','url':'a','relevance_score':.98,'freshness_score':.86,'source_display_name':'A'},
 {'title':'Steven Lorentz clears waivers, preserving options for Maple Leafs','summary':'Steven Lorentz clears waivers for Toronto.','url':'b','relevance_score':.98,'freshness_score':.86,'source_display_name':'B'},
 {'title':"Maple Leafs interested in Blue Jackets' Kirill Marchenko",'summary':'Toronto has interest in Kirill Marchenko.','url':'c','relevance_score':.98,'freshness_score':.86,'source_display_name':'C'},
 {'title':'Maple Leafs preseason roster battle takes shape','summary':'Toronto roster decisions remain before opening night.','url':'d','relevance_score':.98,'freshness_score':.86,'source_display_name':'D'},
]
selected,corroborating=_select_story_diversity(items,3)
check('story_diversity_three_subjects',len(selected)==3,[i.get('title') for i in selected])
check('duplicate_story_becomes_corroboration',corroborating==1,corroborating)
check('corroboration_retained',selected[0].get('corroborating_count')==1,selected[0].get('corroborating_sources'))
print(f"Overall status: {'PASS' if not fails else 'FAIL'}"); raise SystemExit(1 if fails else 0)
