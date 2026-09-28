from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from Core.version import ATHENA_VERSION, RELEASE_NAME
from Scout.conversation.router import _compose_live_event_narrative
fail=[]
def check(n,c,d=''):
 print(f"[{'PASS' if c else 'FAIL'}] {n}: {d}"); fail.append(n) if not c else None
check('version',tuple(map(int, ATHENA_VERSION.split('.'))) >= (0,6,5,0,1),ATHENA_VERSION)
check('release',bool(RELEASE_NAME),RELEASE_NAME)
events=[{'title':'Story A'},{'title':'Story B'}]
n=_compose_live_event_narrative('Maple Leafs news',{'events':events,'ignored_count':2},events)
check('narrative_not_story_dump','Story A' not in n and 'Story B' not in n,n)
studio=(ROOT/'Scout/app.py').read_text(encoding='utf-8')
check('yellow_external_headline','color:#f3d77a' in studio)
check('unified_source_item','renderSourceItem' in studio and 'Details' in studio)
check('more_results','more_source_links' in studio and 'More Results' in studio)
check('investigate_further',"content:'Investigate Further'" in studio)
check('prompt_action','askSuggestedPrompt(${turnId}, ${idx})' in studio and 'turn.prompts[idx]' in studio)
check('turn_action_scope', 'const answerTurnActions = new Map()' in studio and 'turn.moreSources : turn.sources' in studio and 'turn.cards[idx]' in studio)
router=(ROOT/'Scout/conversation/router.py').read_text(encoding='utf-8')
app=studio
check('more_results_hidden_css', '.more-results-body[hidden] { display:none; }' in app, 'explicit hidden-state CSS')
check('evidence_derived_public_intro', '_event_theme_counts' in router and 'Current coverage is centered on' in router, '11.1 evidence-derived synthesis preserved')
check('internal_discovery_hidden', 'internal = display.casefold()' in router and 'current news discovery' in router, 'discovery label kept internal')


raise SystemExit(1 if fail else 0)
