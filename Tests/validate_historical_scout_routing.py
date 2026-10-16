"""Focused regression for longitudinal historical league routing."""
from __future__ import annotations
from pathlib import Path
import json, sys, tempfile
from unittest.mock import patch
PROJECT_ROOT=Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0,str(PROJECT_ROOT))
from Core.version import ATHENA_VERSION, RELEASE_NAME
from Athena.intent_resolution import select_executable_route
from Athena.request_execution import AthenaRequest, execute_request
from Knowledge.LeagueHistory.evidence_registry import discover_historical_evidence
from Scout.conversation.context import ScoutContext
from Scout.conversation.orchestration import scout_intent_plan

def check(label, condition, detail, failures):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}: {detail}")
    if not condition: failures.append(label)

def main():
    failures=[]
    print('Historical Scout Routing Validation'); print('='*72)
    check('version', tuple(map(int, ATHENA_VERSION.split('.'))) >= (0,6,5,0,1), ATHENA_VERSION, failures)
    check('release', bool(RELEASE_NAME), RELEASE_NAME, failures)
    prompts=[
      'What can you tell me about how the JHLPAA draft has changed over the last 10 seasons?',
      'How has drafting in my league changed over the past five seasons?',
      'Show me the history of our league draft across seasons.',
    ]
    for i,prompt in enumerate(prompts,1):
        plan=scout_intent_plan(prompt,'fantasy')
        check(f'longitudinal_route_{i}', plan is not None and plan.route=='fantasy_longitudinal_draft', plan, failures)
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); d=root/'Output'/'Historical'
        for season,slots,selections,state in [(2024,280,140,'completed'),(2025,280,129,'completed')]:
            sd=d/str(season); sd.mkdir(parents=True)
            (sd/'draft_results_canonical.json').write_text(json.dumps({'season':season,'provider':'Fantrax','provider_league_id':f'id{season}','draft_state':state,'configured_slot_count':slots,'selection_count':selections,'no_player_selection_count':slots-selections}),encoding='utf-8')
        evidence=discover_historical_evidence('draft',project_root=root)
        check('canonical_output_path', 'Output/Historical/' in evidence['seasons'][0].get('artifact',''), evidence['seasons'][0].get('artifact') if evidence.get('seasons') else evidence, failures)
        check('registry_available', evidence.get('status')=='available', evidence, failures)
        check('registry_coverage', evidence.get('coverage')==2, evidence.get('coverage'), failures)
        check('registry_range', (evidence.get('first_season'),evidence.get('last_season'))==(2024,2025), (evidence.get('first_season'),evidence.get('last_season')), failures)
        check('provider_state_preserved', evidence['seasons'][0].get('provider_draft_state')=='completed', evidence['seasons'][0], failures)
    question='How has the JHLPAA draft changed over the last 10 seasons?'
    route, owner=select_executable_route(question,'fantasy')
    fixture_seasons=[
      {'season':2024,'selections':140,'configured_slots':280,'identity_available':True,
       'resolved_team_names':120,'resolved_player_names':90,'resolved_positions':130,
       'artifact':'fixture/2024/draft_results_canonical.json'},
      {'season':2025,'selections':129,'configured_slots':280,'identity_available':True,
       'resolved_team_names':110,'resolved_player_names':85,'resolved_positions':120,
       'artifact':'fixture/2025/draft_results_canonical.json'},
    ]
    with patch('Knowledge.LeagueHistory.evidence_registry.discover_historical_evidence',return_value={'status':'available','seasons':fixture_seasons}), \
         patch('Knowledge.Intelligence.Fantasy.historical_draft.build_historical_draft_intelligence',return_value={'status':'missing','findings':[],'files_read':[]}):
        answer=execute_request(AthenaRequest(question,mode='fantasy',context=ScoutContext()))
    trace=(answer.get('developer') or {}).get('inquiry_execution_trace') or {}
    missing=(answer.get('developer') or {}).get('missing_or_limited') or []
    limitations=' '.join(answer.get('known_limitations') or []).lower()
    check('athena_owns_historical_route', route=='fantasy_longitudinal_draft' and owner=='athena_intent_plan' and trace.get('invocation',{}).get('owner')=='athena_registered_specialist', (route,owner), failures)
    check('identity_limits_are_reported_from_fixture', {'historical_manager_identity','historical_franchise_continuity'}.issubset(set(missing)) and 'manager tendencies require resolved same-season manager identity' in limitations, missing, failures)
    handler_source=(PROJECT_ROOT/'Athena'/'capability_handlers.py').read_text(encoding='utf-8')
    check('no_jhlpaa_counts_hardcoded', '280, 129' not in handler_source and '2016' not in handler_source, 'runtime evidence drives comparison', failures)
    print('-'*72); print('Overall status:', 'FAIL' if failures else 'PASS')
    return 1 if failures else 0
if __name__=='__main__': raise SystemExit(main())
