"""Focused regression for longitudinal historical league routing."""
from __future__ import annotations
from pathlib import Path
import json, sys, tempfile
PROJECT_ROOT=Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0,str(PROJECT_ROOT))
from Core.version import ATHENA_VERSION, RELEASE_NAME
from Knowledge.LeagueHistory.evidence_registry import discover_historical_evidence
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
    source=(PROJECT_ROOT/'Scout'/'conversation'/'orchestration.py').read_text(encoding='utf-8')
    check('progressive_limitations', 'historical_manager_identity' in source and 'historical_player_identity' in source, 'same-season identity boundary declared', failures)
    check('no_jhlpaa_counts_hardcoded', '280, 129' not in source and '2016' not in source, 'runtime evidence drives comparison', failures)
    print('-'*72); print('Overall status:', 'FAIL' if failures else 'PASS')
    return 1 if failures else 0
if __name__=='__main__': raise SystemExit(main())
