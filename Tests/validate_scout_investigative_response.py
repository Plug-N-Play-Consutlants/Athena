from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from Scout.conversation.router import _clean_event_text, _event_source_links, _event_followup_prompts
from Core.version import ATHENA_VERSION, RELEASE_NAME
fail=[]
def check(n,c,d=''):
 print(f"[{'PASS' if c else 'FAIL'}] {n}: {d}"); fail.append(n) if not c else None
check('version',tuple(map(int, ATHENA_VERSION.split('.'))) >= (0,6,5,0,1),ATHENA_VERSION)
check('release',bool(RELEASE_NAME),RELEASE_NAME)
check('html_entity_decode',_clean_event_text('Ontario junior hockey &nbsp;&nbsp; CP24')=='Ontario junior hockey CP24')
events=[{'title':'Why the Maple Leafs placed Steven Lorentz on waivers','summary':'Why the Maple Leafs placed Steven Lorentz on waivers','source_display_name':'Toronto Sun','published_at':'Sep 24','url':'https://example.test/a'},{'title':'Maple Leafs linked to Marchenko','summary':'Toronto is reportedly interested in the winger','source_display_name':'Sportsnet','url':'https://example.test/b'}]
links=_event_source_links(events)
check('descriptive_source_label',links[0]['label'].startswith('Why the Maple Leafs'),links[0])
check('publisher_exposed',links[0]['publisher']=='Toronto Sun',links[0])
check('duplicate_summary_suppressed',links[0]['summary']=='',links[0])
prompts=_event_followup_prompts(events)
check('evidence_derived_followups',len(prompts)>=2,prompts)
studio=(ROOT/'Scout/app.py').read_text(encoding='utf-8')
check('studio_renders_suggested_prompts','renderSuggestedPrompts(answer, turnId)' in studio and 'askText(item.text, item.continuation)' in studio)
check('studio_external_links','target="_blank"' in studio and 'noopener noreferrer' in studio)
raise SystemExit(1 if fail else 0)
