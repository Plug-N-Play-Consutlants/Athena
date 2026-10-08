"""Regression validation for canonical NHL team economic/roster state."""
from pathlib import Path
import sys
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from Core.version import ATHENA_VERSION, RELEASE_NAME
from Knowledge.Teams.team_economic_state import resolve_team_economic_state
from Athena.intent_planner import plan_capability
from Athena.execution_registry import SPECIALISTS, execute_specialist

def main():
    checks=[]
    def check(name,ok,detail=""):
        checks.append(bool(ok)); print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    check("version",tuple(map(int,ATHENA_VERSION.split('.'))) >= (0,7,2,0,0),ATHENA_VERSION)
    check("release_metadata_available",bool(RELEASE_NAME.strip()),RELEASE_NAME)
    team=resolve_team_economic_state(team_id="nhl.team.tor")
    check("team_identity",team.team_name=="Toronto Maple Leafs" and team.league_year=="2026-27",team.to_dict())
    check("preseason_not_final",team.roster_evidence_status=="preseason_not_final",team.roster_evidence_status)
    check("aggregate_blocked",not team.aggregate_permitted and team.aggregate_cap_usage_status=="unavailable_incomplete_ledger",team.aggregate_cap_usage_status)
    covered=team.covered_contracts()
    check("contract_reconciliation",len(covered)==1 and covered[0].player_name=="Auston Matthews",[c.player_name for c in covered])
    plan=plan_capability("Maple Leafs salary cap usage this year","public")
    check("athena_plans_cap_reasoning_over_team_state",getattr(plan,"route",None)=="public_nhl_cap_reasoning",getattr(plan,"route",None))
    check("registered","public_nhl_team_economic_state" in SPECIALISTS)
    ans=execute_specialist("public_nhl_team_economic_state",SimpleNamespace(files_loaded=[]),"Maple Leafs salary cap usage this year",mode="public")
    text=(ans or {}).get("natural_language_response","")
    check("athena_consumes_team_state","$104.0M" in text and "Auston Matthews" in text,text)
    check("no_false_aggregate","not complete enough to state actual cap usage or cap space" in text and "will not add" in text,text)
    check("adjustment_gap_explicit","team_cap_adjustment_ledger" in str((ans or {}).get("developer",{})),str((ans or {}).get("developer",{}).get("missing_or_limited",[])))
    print(f"Overall status: {'PASS' if all(checks) else 'FAIL'}")
    return 0 if all(checks) else 1
if __name__=="__main__": raise SystemExit(main())
