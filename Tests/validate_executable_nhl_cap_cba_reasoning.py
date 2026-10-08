"""Acceptance validation for v0.7.3 executable NHL cap/CBA reasoning."""
from pathlib import Path
import sys
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from Core.version import ATHENA_VERSION, RELEASE_NAME
from Knowledge.Teams.team_economic_state import resolve_team_economic_state
from Knowledge.Economics.league_season_context import resolve_league_season_context
from Reasoning.Cap.cap_reasoning import ADJUSTMENT_CLASSES, evaluate_team_cap_state
from Athena.intent_planner import plan_capability
from Athena.execution_registry import SPECIALISTS, execute_specialist

def main():
    checks=[]
    def check(name,ok,detail=""):
        checks.append(bool(ok)); print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    check("version",tuple(map(int,ATHENA_VERSION.split('.'))) >= (0,7,3,0,0),ATHENA_VERSION)
    check("release_metadata_present",bool(RELEASE_NAME),RELEASE_NAME)
    team=resolve_team_economic_state(team_id="nhl.team.tor")
    econ=resolve_league_season_context(league_year=team.league_year)
    d=evaluate_team_cap_state(team,econ)
    check("incomplete_ledger_indeterminate",d.status=="indeterminate_incomplete_ledger" and d.headroom is None,d.to_dict())
    check("adjustments_explicit",all(x in d.unresolved_inputs for x in ADJUSTMENT_CLASSES),d.unresolved_inputs)
    check("effective_cba_applied",d.cba_environment_id==econ.cba_environment_id and "applicable_cba_environment" in d.rules_applied,d.rules_applied)
    class CompleteTeam:
        team_id="test"; team_name="Test Club"; as_of="2026-10-01"; aggregate_permitted=True
    ok=evaluate_team_cap_state(CompleteTeam(),econ,verified_cap_charge_total=100_000_000,resolved_adjustment_classes=ADJUSTMENT_CLASSES)
    check("complete_ledger_executes",ok.status=="within_team_payroll_range" and ok.headroom==4_000_000 and ok.floor_margin==23_100_000,ok.to_dict())
    over=evaluate_team_cap_state(CompleteTeam(),econ,verified_cap_charge_total=105_000_000,resolved_adjustment_classes=ADJUSTMENT_CLASSES)
    check("upper_limit_executes",over.status=="above_upper_limit" and over.headroom==-1_000_000,over.to_dict())
    under=evaluate_team_cap_state(CompleteTeam(),econ,verified_cap_charge_total=70_000_000,resolved_adjustment_classes=ADJUSTMENT_CLASSES)
    check("lower_limit_executes",under.status=="below_lower_limit" and under.floor_margin==-6_900_000,under.to_dict())
    plan=plan_capability("Maple Leafs salary cap usage this year","public")
    check("athena_plans_cap_reasoning",getattr(plan,"route",None)=="public_nhl_cap_reasoning",getattr(plan,"route",None))
    check("registered","public_nhl_cap_reasoning" in SPECIALISTS)
    ans=execute_specialist("public_nhl_cap_reasoning",SimpleNamespace(files_loaded=[]),"Maple Leafs salary cap usage this year",mode="public")
    text=(ans or {}).get("natural_language_response","")
    check("athena_applies_rules","$104.0M" in text and "2026 NHL/NHLPA CBA" in text and "cannot determine" in text,text)
    check("no_partial_sum_as_payroll","Auston Matthews" in text and "not treating those covered contracts" in text,text)
    dev=(ans or {}).get("developer",{})
    check("structured_determination",dev.get("cap_determination",{}).get("status")=="indeterminate_incomplete_ledger",dev.get("cap_determination"))
    print(f"Overall status: {'PASS' if all(checks) else 'FAIL'}")
    return 0 if all(checks) else 1
if __name__=="__main__": raise SystemExit(main())
