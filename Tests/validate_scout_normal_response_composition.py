from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.version import ATHENA_VERSION, RELEASE_NAME
from Scout.conversation.responses import response

failures=[]
def check(name, ok, detail=''):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    if not ok: failures.append(name)

check('version', tuple(map(int, ATHENA_VERSION.split('.'))) >= (0,6,5,0,1), ATHENA_VERSION)
check('release_name', bool(RELEASE_NAME), RELEASE_NAME)

live_narrative = (
    'I found 3 recent NHL event item(s) from the configured live sources.\n\n'
    '1. Maple Leafs roster decision. Source: discovery; date: today.\n\n'
    '2. Maple Leafs preseason development. Source: discovery; date: today.'
)
live = response(
    intent='live_event_intelligence', title='Recent NHL events',
    engine_conclusion='Scout selected source-backed live/cached event evidence for this recent-event question.',
    natural_language_response=live_narrative,
    observed_facts=['news: Maple Leafs roster decision', 'news: Maple Leafs preseason development'],
)
check('live_public_keeps_event_narrative', 'Maple Leafs roster decision' in live.get('public_comment','') and 'preseason development' in live.get('public_comment',''), live.get('public_comment',''))
check('live_public_not_generic_conclusion', live.get('public_comment','') != live.get('engine_conclusion',''), live.get('public_comment',''))

predraft_narrative = ('The current evidence describes a 2026 pre-draft state with 154 rostered players across 14 teams. '
                     'The draft board contains 280 configured slots across 20 rounds, with current ownership ranging from 17 to 23 slots per team.')
predraft = response(
    intent='fantasy_pre_draft_context', title='2026 pre-draft context',
    engine_conclusion='Athena combined current keeper state, current draft-capital ownership, available-pool evidence, and historical draft intelligence without converting any of them into a selection prediction.',
    natural_language_response=predraft_narrative,
    observed_facts=['Rostered pre-draft players: 154.', 'Supplied Fantrax export contains 7028 rows marked FA; this is contextual evidence, not a live availability guarantee.'],
)
public = predraft.get('public_comment','')
check('predraft_public_keeps_context', '154 rostered players' in public and '280 configured slots' in public, public)
check('predraft_public_keeps_material_pool_evidence', '7028 rows marked FA' in public, public)
check('predraft_public_keeps_bounded_conclusion', 'without converting any of them into a selection prediction' in public, public)

router_text=(ROOT/'Scout/conversation/router.py').read_text(encoding='utf-8')
check('live_route_composes_natural_before_payload', 'natural_language_response=natural' in router_text, 'natural narrative enters response() before public_comment composition')

if failures:
    raise SystemExit(1)
print('Scout Normal Response Composition Validation: PASS')
