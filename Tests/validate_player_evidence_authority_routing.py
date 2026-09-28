from Athena.intent_planner import plan_capability
from Athena.request_execution import AthenaRequest, execute_request
from Scout.conversation.context import load_context

fails=[]
def check(name, ok, detail=''):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ''))
    if not ok: fails.append(name)

plan=plan_capability("How has Connor McDavid's NHL performance changed over the last 3 seasons?", "public")
check('temporal_history_route', plan is not None and plan.route=='public_player_temporal_comparison', getattr(plan,'route',None))

ctx=load_context()
ans=execute_request(AthenaRequest(question="How has Connor McDavid's NHL performance changed over the last 3 seasons?", mode='public', context=ctx))
check('temporal_executes_player_path', ans.get('intent')=='public_player_temporal_comparison', str(ans.get('intent')))
check('temporal_not_rules', 'minimum salary' not in str(ans).casefold() and 'contract term' not in str(ans).casefold())

ctx=load_context()
cmp=execute_request(AthenaRequest(question='Compare Connor McDavid and Nathan MacKinnon based on their recent NHL performance', mode='public', context=ctx))
text=str(cmp.get('natural_language_response') or cmp.get('response') or cmp)
check('comparison_has_verified_stats', 'verified nhl statistical context' in text.casefold(), text[:180])
check('comparison_no_false_stats_gap', 'official current-season stats' not in text.casefold())
check('comparison_bundle_attached', getattr(ctx,'request_evidence',{}).get('status') in {'ready','partial'})

# Continuation should qualify an otherwise ambiguous same-name player question.
from Knowledge.Intelligence.Entities.entity_registry import entities_by_type
swedish=next((e for e in entities_by_type('player') if e.canonical_name=='Sebastian Aho' and e.position=='D'), None)
if swedish:
    ctx=load_context()
    follow=execute_request(AthenaRequest(question="What are the biggest evidence-backed uncertainties in Sebastian Aho's outlook?", mode='public', context=ctx, continuation={'origin_intent':'public_player_profile','subject_entity_id':swedish.entity_id}))
    check('selected_aho_continuity', follow.get('intent')!='public_entity_disambiguation', str(follow.get('intent')))
else:
    check('selected_aho_continuity', False, 'Swedish Aho entity unavailable')

raise SystemExit(1 if fails else 0)
