from Intelligence.Investigation import EvidenceCandidate, InvestigationSessionRegistry, prepare_runtime_context

def main():
    print('Adaptive Investigation Runtime Integration Doctor')
    print('='*64)
    checks=[]
    def c(name, cond, detail=''):
        checks.append(bool(cond)); print(f"[{'PASS' if cond else 'FAIL'}] {name}: {detail}")
    reg=InvestigationSessionRegistry()
    ctx=prepare_runtime_context('live_event_intelligence','Recent Leafs news',entities=('toronto_maple_leafs',),evidence_candidates=(
        EvidenceCandidate('fallback',('toronto_maple_leafs',),'Most recent Leafs evidence','Trusted fallback','2026-08-31T10:00:00+00:00','official',0.9,False,True),
        EvidenceCandidate('wrong',('montreal_canadiens',),'Unrelated live event','Must not be selected','2026-09-01T10:00:00+00:00','official',0.99,True,True),
    ))
    c('runtime_version', ctx.to_dict()['version']=='0.6.4.1.0', ctx.to_dict()['version'])
    c('strategy_operational', ctx.plan.strategy.strategy_id=='news_update', ctx.plan.strategy.strategy_id)
    c('graceful_fallback', ctx.evidence_selection.tier=='recent_fallback', ctx.evidence_selection.tier)
    c('fallback_entity_safe', [i.evidence_id for i in ctx.evidence_selection.items]==['fallback'], str([i.evidence_id for i in ctx.evidence_selection.items]))
    rich=prepare_runtime_context('public_player_profile','Tell me about Matthews',entities=('auston_matthews',),registry=reg,session_id='doctor')
    follow=prepare_runtime_context('public_player_explainability','Why?',entities=('auston_matthews',),registry=reg,session_id='doctor')
    c('rich_output_preserved', rich.plan.composition.preserve_rich_output, rich.plan.composition.profile)
    c('investigation_continuity', follow.continued_state, follow.state.investigation_id if follow.state else '')
    print('-'*64); print(f"Overall status: {'PASS' if all(checks) else 'FAIL'}")
    return 0 if all(checks) else 1
if __name__=='__main__': raise SystemExit(main())
