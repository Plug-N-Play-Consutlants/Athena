from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from Core.version import ATHENA_VERSION, RELEASE_NAME
from Scout.conversation.orchestration import scout_intent_plan, comparison_semantics
from Scout.conversation.router import route_question, _focused_live_events, _focused_live_narrative, _investigative_scenario_context, _investigation_followup_prompts
from Scout.conversation.context import load_context

fail=[]
def check(name, ok, detail=''):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    if not ok: fail.append(name)

check('version', tuple(map(int, ATHENA_VERSION.split('.'))) >= (0, 6, 5, 1, 5), ATHENA_VERSION)
check('release', bool(RELEASE_NAME.strip()), RELEASE_NAME)
cases=[
 ('draft_paraphrase','fantasy','Analyze my draft','fantasy_pre_draft_context'),
 ('temporal_comparison','public',"How does Auston Matthews's current production compare with his recent career baseline?",'public_player_temporal_comparison'),
 ('entity_comparison','public','Auston Matthews vs Connor McDavid','public_player_comparison'),
 ('lifecycle_entity_comparison','public','Auston Matthews vs Gavin McKenna','public_player_comparison'),
 ('contextual_surname_comparison','public','Matthews vs McKenna','public_player_comparison'),
 ('event_investigation','public','Investigate the reported acquisition story behind “Report: Maple Leafs among teams interested in Kirill Marchenko - The Leafs Nation” and what it could mean.','live_event_intelligence'),
]
for name,mode,q,expected in cases:
    plan=scout_intent_plan(q,mode)
    check(name, bool(plan and plan.route==expected), getattr(plan,'route',None))
ctx=load_context()
temporal=route_question(cases[1][2],ctx,mode='public')
check('temporal_executes', temporal.get('intent')=='public_player_temporal_comparison', temporal.get('intent'))
check('temporal_not_two_player_gap', temporal.get('intent')!='public_player_comparison_gap', temporal.get('title'))
mckenna=route_question('Auston Matthews vs Gavin McKenna',ctx,mode='public')
short_mckenna=route_question('Matthews vs McKenna',ctx,mode='public')
check('lifecycle_comparison_executes', mckenna.get('intent')=='public_player_comparison', mckenna.get('intent'))
check('contextual_surname_comparison_executes', short_mckenna.get('intent')=='public_player_comparison' and 'Gavin McKenna' in str(short_mckenna.get('title') or ''), short_mckenna.get('title'))
check('contextual_surname_assumption_visible', 'treating McKenna as Gavin McKenna' in str(short_mckenna.get('natural_language_response') or ''), str(short_mckenna.get('natural_language_response') or '')[:180])
check('lifecycle_comparison_not_single_player', 'Gavin McKenna' in str(mckenna.get('title') or '') and 'Auston Matthews' in str(mckenna.get('title') or ''), mckenna.get('title'))

check('comparison_subjects_survive_response', all(name in str(mckenna.get('natural_language_response') or '') for name in ['Auston Matthews','Gavin McKenna']), str(mckenna.get('natural_language_response') or '')[:220])
check('comparison_not_truncated', len(str(mckenna.get('natural_language_response') or '')) > 180, len(str(mckenna.get('natural_language_response') or '')))

player_current=scout_intent_plan("What has Auston Matthews shown in camp and preseason, and does it change the outlook for his early-season form or deployment?","public")
check('player_current_event_route', bool(player_current and player_current.route=='public_player_investigation'), getattr(player_current,'route',None))
mock_events=[
 {'title':'Report: Maple Leafs among teams interested in Kirill Marchenko - The Leafs Nation','summary':'Toronto is reported among interested teams.','source_display_name':'The Leafs Nation'},
 {'title':'Unrelated Leafs roster story','summary':'Other roster news.','source_display_name':'Other'},
]
focused,focus=_focused_live_events(cases[5][2],mock_events)
check('focused_story_selection', focus=='referenced_story' and len(focused)==1 and 'Marchenko' in focused[0]['title'], f'{focus}:{len(focused)}')
focused_text=_focused_live_narrative(cases[5][2],focused,focus)
check('focused_story_synthesis', 'reported interest' in focused_text and 'both organizations' in focused_text and 'Athena would' not in focused_text and "Athena's current evidence" not in focused_text, focused_text[:220])
contract=_investigative_scenario_context(cases[5][2],focused)
check('investigative_contract_stages', contract.get('stages')==['claim_provenance','corroboration_and_contradiction','contextual_feasibility','bounded_scenario_analysis','bilateral_impact','current_conclusion','revision_triggers'], contract.get('stages'))
check('uncorroborated_not_false', contract.get('corroboration_state')=='single_selected_report', contract.get('corroboration_state'))
check('temporal_evidence_principle', any('evidence available when it was made' in x for x in contract.get('temporal_principles',[])), 'temporal conclusion contract')
check('lifecycle_comparison_substantive', 'different career stages' in str(mckenna.get('natural_language_response') or '').lower() and len(mckenna.get('observed_facts') or [])>=3, str(mckenna.get('natural_language_response') or '')[:180])

player_events=[{'title':'Flyers preseason story','summary':'Trevor Zegras preseason update','source_display_name':'ESPN'}]
focused_player,player_focus=_focused_live_events("What has Auston Matthews shown in camp and preseason?",player_events)
check('targeted_player_rejects_unrelated_evidence', player_focus=='player_current_event_no_match' and focused_player==[], f'{player_focus}:{len(focused_player)}')
aho=route_question('Sebastian Aho',ctx,mode='public')
aho_cards=aho.get('cards') or []
check('aho_disambiguation_cards', aho.get('intent')=='public_entity_disambiguation' and len(aho_cards)>=2 and all(card.get('action')=='ask_prompt' and card.get('prompt') for card in aho_cards[:2]), str(aho_cards[:2]))
check('aho_cards_canonical_choices', any('CAR' in str(card.get('label')) for card in aho_cards) and any('Sweden' in str(card.get('label')) for card in aho_cards), str([card.get('label') for card in aho_cards]))
check('aho_cards_render_normal_mode', 'cards ? `<div class=\"cards\">${cards}</div>`' in (ROOT/'Scout/app.py').read_text(encoding='utf-8'), 'actionable cards rendered outside developer mode')
icing=route_question('What is icing',ctx,mode='public')
check('question_not_player_identity', icing.get('intent') not in {'public_player_profile','public_player_lifecycle'}, icing.get('intent'))
from Knowledge.Intelligence.Public.player_lifecycle import resolve_player_lifecycle
icing_lifecycle=resolve_player_lifecycle('What is icing',allow_network=False)
check('lifecycle_rejects_question_identity', icing_lifecycle.get('status')=='not_person_query', icing_lifecycle.get('status'))
inv_prompts=_investigation_followup_prompts(cases[5][2],focused)
check('investigation_followups_stay_on_subject', len(inv_prompts)>=3 and any('salary-cap' in x for x in inv_prompts) and any('other organization' in x for x in inv_prompts) and not any('camp and preseason' in x for x in inv_prompts), inv_prompts)

draft=route_question(cases[0][2],ctx,mode='fantasy')
check('draft_executes', draft.get('intent')=='fantasy_pre_draft_context', draft.get('intent'))
app=(ROOT/'Scout/app.py').read_text(encoding='utf-8')
check('enum_humanizer', 'humanizeCardValue' in app and "split('_')" in app, 'card presentation')
check('card_containment', 'overflow-wrap:anywhere' in app and 'min-width:0' in app, 'CSS containment')
router=(ROOT/'Scout/conversation/router.py').read_text(encoding='utf-8')
check('no_per_active_manager_fact', 'per active manager.' not in router, 'presentation terminology')
rel=comparison_semantics('How have Auston Matthews and Connor McDavid performed head-to-head and when they played together?')
check('relationship_semantics_reserved', rel.get('class')=='relationship' and rel.get('relationship_contract',{}).get('sport_neutral') is True, rel)


# v0.6.5.1.4 knowledge interpretation composition regression gates
icing_answer=route_question('What is icing?',ctx,mode='public')
icing_text=str(icing_answer.get('natural_language_response') or '')
check('icing_composes_answer', 'In hockey, icing' in icing_text and 'Athena found public hockey knowledge-pack evidence' not in icing_text, icing_text)
cap_answer=route_question('What roster and salary-cap structures could make this acquisition workable?',ctx,mode='public')
cap_text=str(cap_answer.get('natural_language_response') or '')
check('cap_scenario_composes_constraints', 'acquiring club' in cap_text and 'current payrolls' in cap_text and 'Athena found public hockey knowledge-pack evidence' not in cap_text, cap_text)
current_cap=route_question('Maple Leafs salary cap impact right now',ctx,mode='public')
current_cap_text=str(current_cap.get('natural_language_response') or '')
check('current_cap_does_not_mistake_rules_for_state', 'does not establish the team\'s current cap position' in current_cap_text, current_cap_text)


print('-'*64)
print('Overall status:', 'PASS' if not fail else 'FAIL')
raise SystemExit(1 if fail else 0)
