"""Acceptance validation for v0.7.4 transaction/scenario engine."""
from pathlib import Path
import sys
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from Core.version import ATHENA_VERSION,RELEASE_NAME
from Knowledge.Teams.team_economic_state import resolve_team_economic_state
from Knowledge.Economics.league_season_context import resolve_league_season_context
from Knowledge.Contracts.player_contract_state import resolve_player_contract_state
from Reasoning.Cap.cap_reasoning import ADJUSTMENT_CLASSES
from Reasoning.Transactions.scenario_engine import acquire_contract,release_contract,evaluate_transaction_scenario
from Athena.intent_planner import plan_capability
from Athena.execution_registry import SPECIALISTS,execute_specialist

def main():
 r=[]
 def c(n,o,d=""):r.append(bool(o));print(f"[{'PASS' if o else 'FAIL'}] {n}: {d}")
 c('version',tuple(map(int,ATHENA_VERSION.split('.'))) >= (0,7,4,0,0),ATHENA_VERSION);c('release_metadata_present',bool(RELEASE_NAME),RELEASE_NAME)
 team=resolve_team_economic_state(team_id='nhl.team.tor');econ=resolve_league_season_context(league_year=team.league_year);mc=resolve_player_contract_state(player_entity_id='nhl.player.connor_mcdavid',as_of=team.as_of);am=resolve_player_contract_state(player_entity_id='nhl.player.auston_matthews',as_of=team.as_of)
 incoming=acquire_contract(mc);c('canonical_acquisition_delta',incoming.cap_charge_delta==12_500_000,incoming.to_dict())
 outgoing=release_contract(am);c('canonical_release_delta',outgoing.cap_charge_delta==-13_250_000,outgoing.to_dict())
 sc=evaluate_transaction_scenario(team,econ,scenario_id='test:tor:mcdavid',operations=(incoming,));c('partial_baseline_stays_indeterminate',sc.status=='scenario_indeterminate' and sc.net_cap_charge_delta==12_500_000 and sc.hypothetical_cap_charge_total is None,sc.to_dict())
 c('canonical_state_not_mutated',team.covered_contracts()[0].player_name=='Auston Matthews' and len(team.covered_contracts())==1)
 class CompleteTeam:
  team_id='test';team_name='Test Club';as_of='2026-10-01';aggregate_permitted=True
 done=evaluate_transaction_scenario(CompleteTeam(),econ,scenario_id='test:complete',operations=(incoming,),verified_baseline_cap_charge_total=90_000_000,resolved_adjustment_classes=ADJUSTMENT_CLASSES)
 c('complete_scenario_executes',done.status=='scenario_evaluated' and done.hypothetical_cap_charge_total==102_500_000 and done.cap_determination['status']=='within_team_payroll_range',done.to_dict())
 retained=acquire_contract(mc,retained_cap_amount=2_500_000);c('explicit_retention_delta_only',retained.cap_charge_delta==10_000_000 and retained.retained_cap_amount==2_500_000,retained.to_dict())
 plan=plan_capability('What if the Maple Leafs acquire Connor McDavid?','public');c('athena_plans_scenario',getattr(plan,'route',None)=='public_nhl_transaction_scenario',getattr(plan,'route',None));c('registered','public_nhl_transaction_scenario' in SPECIALISTS)
 ans=execute_specialist('public_nhl_transaction_scenario',SimpleNamespace(files_loaded=[]),'What if the Maple Leafs acquire Connor McDavid?',mode='public');text=(ans or {}).get('natural_language_response','');c('athena_executes_scenario','+$12.50M' not in text and 'adds $12.50M' in text and 'final cap usage/headroom remains indeterminate' in text,text);dev=(ans or {}).get('developer',{});c('scenario_structured',dev.get('transaction_scenario',{}).get('net_cap_charge_delta')==12_500_000,dev.get('transaction_scenario'));c('current_state_preserved',dev.get('canonical_team_state_unchanged',{}).get('canonical_contract_coverage',{}).get('covered_players')==['Auston Matthews'])
 print(f"Overall status: {'PASS' if all(r) else 'FAIL'}");return 0 if all(r) else 1
if __name__=='__main__':raise SystemExit(main())
