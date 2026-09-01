"""Validate Adaptive Investigation Strategy Foundation."""
from __future__ import annotations
from pathlib import Path
import sys
PROJECT_ROOT=Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0,str(PROJECT_ROOT))
from Core.version import ATHENA_VERSION, RELEASE_NAME, VERSION_SCHEMA
from Intelligence.Investigation import build_investigation_plan, investigation_diagnostics, InvestigationSessionRegistry
from Intelligence.Foundation.module_contracts import seed_module_contract_registry

def check(label, condition, detail, failures):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}: {detail}")
    if not condition: failures.append(label)

def main():
    failures=[]
    print('Adaptive Investigation Strategy Validation'); print('='*68)
    check('version', ATHENA_VERSION == '0.6.4.1.0', ATHENA_VERSION, failures)
    check('release', RELEASE_NAME == 'Adaptive Investigation Runtime Integration', RELEASE_NAME, failures)
    check('schema', VERSION_SCHEMA == 'major.epic.sprint.patch.hotfix', VERSION_SCHEMA, failures)
    score=build_investigation_plan('score_update')
    news=build_investigation_plan('live_event_intelligence')
    profile=build_investigation_plan('public_player_profile')
    comparison=build_investigation_plan('public_player_comparison')
    deep=build_investigation_plan('public_team_window_analysis')
    advisory=build_investigation_plan('fantasy_trade_directions')
    check('score_is_concise', score.strategy.depth=='concise' and not score.create_working_state, score.to_dict(), failures)
    check('news_is_concise_discoverable', news.strategy.depth=='concise' and news.strategy.discovery_mode=='available', news.to_dict(), failures)
    check('profile_remains_rich', profile.strategy.depth=='rich' and profile.strategy.preserve_rich_output, profile.to_dict(), failures)
    check('comparison_remains_rich', comparison.strategy.depth=='rich' and comparison.composition.profile=='comparison_experience', comparison.to_dict(), failures)
    check('deep_analysis_deep', deep.strategy.depth=='deep' and deep.create_working_state, deep.to_dict(), failures)
    check('advisory_preserves_judgment_path', advisory.strategy.strategy_id=='advisory', advisory.to_dict(), failures)
    check('different_intents_different_strategy', score.strategy.strategy_id != comparison.strategy.strategy_id, (score.strategy.strategy_id,comparison.strategy.strategy_id), failures)
    registry=seed_module_contract_registry(); resolved=registry.resolve_capabilities(('assessment','event_context','comparison_experience'))
    check('module_contract_capability_discovery', bool(resolved['assessment']) and bool(resolved['event_context']) and bool(resolved['comparison_experience']), resolved, failures)
    sessions=InvestigationSessionRegistry(); state=sessions.start('Toronto roster optimization','deep_analysis'); state.add_entity('Toronto Maple Leafs'); state.add_finding('Sample finding'); state.add_open_question('Sample question'); state.record_turn()
    check('working_state_serializable', state.to_dict()['turns']==1 and len(state.to_dict()['findings'])==1, state.to_dict(), failures)
    diag=investigation_diagnostics()
    check('diagnostics_pass', diag['status']=='pass' and diag['preserves_rich_experiences'] and diag['brief_updates'], diag, failures)
    print('-'*68); print('Overall status: '+('FAIL' if failures else 'PASS'))
    if failures: print(f'Failed: {len(failures)}')
    return 1 if failures else 0
if __name__=='__main__': raise SystemExit(main())
