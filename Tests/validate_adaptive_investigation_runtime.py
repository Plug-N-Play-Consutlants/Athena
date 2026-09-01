from Intelligence.Investigation import EvidenceCandidate, InvestigationSessionRegistry, prepare_runtime_context, record_runtime_outcome

def check(name, cond, detail=''):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}: {detail}")
    return bool(cond)

def main():
    ok=[]
    reg=InvestigationSessionRegistry()
    recent=[
      EvidenceCandidate('old_leafs',('toronto_maple_leafs',),'Leafs roster update','Older trustworthy Leafs item','2026-08-25T12:00:00+00:00','official',0.9,False,True),
      EvidenceCandidate('other',('montreal_canadiens',),'Canadiens trade','Unrelated current item','2026-09-01T01:00:00+00:00','official',0.95,True,True),
    ]
    news=prepare_runtime_context('live_event_intelligence','Recent Leafs news',entities=('toronto_maple_leafs',),evidence_candidates=recent)
    ok += [check('news_strategy', news.plan.strategy.strategy_id=='news_update', news.plan.strategy.strategy_id)]
    ok += [check('news_concise', news.plan.strategy.depth=='concise', news.plan.strategy.depth)]
    ok += [check('fallback_used', news.evidence_selection.tier=='recent_fallback', news.evidence_selection.tier)]
    ids=[x.evidence_id for x in news.evidence_selection.items]
    ok += [check('no_unrelated_substitution', ids==['old_leafs'], str(ids))]
    rich=prepare_runtime_context('public_player_comparison','Compare McDavid and MacKinnon',entities=('connor_mcdavid','nathan_mackinnon'),registry=reg,session_id='s1')
    ok += [check('comparison_rich', rich.plan.strategy.depth=='rich', rich.plan.strategy.depth)]
    ok += [check('preserve_rich', rich.plan.composition.preserve_rich_output, str(rich.plan.composition.preserve_rich_output))]
    record_runtime_outcome(rich, findings=('McDavid and MacKinnon comparison established.',),open_questions=('Compare playoff translation?',))
    follow=prepare_runtime_context('public_player_comparison','What about playoff translation?',entities=('connor_mcdavid',),registry=reg,session_id='s1')
    ok += [check('working_state_continues', follow.continued_state, follow.state.investigation_id if follow.state else '')]
    ok += [check('working_state_retains_findings', bool(follow.state and follow.state.findings), str(follow.state.findings if follow.state else []))]
    print(f"Overall status: {'PASS' if all(ok) else 'FAIL'}")
    return 0 if all(ok) else 1

if __name__=='__main__': raise SystemExit(main())
