"""Acceptance validation for v0.7.6 organizational environment/plausibility."""
from __future__ import annotations
from pathlib import Path
import sys
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from Core.version import ATHENA_VERSION,RELEASE_NAME
from Athena.intent_planner import plan_capability
from Athena.execution_registry import SPECIALISTS,execute_specialist
def main():
 checks=[]
 def check(n,ok,d=""):checks.append(bool(ok));print(f"[{'PASS' if ok else 'FAIL'}] {n}: {d}")
 check("version",tuple(map(int,ATHENA_VERSION.split("."))) >= (0,7,6,0,0),ATHENA_VERSION)
 check("release",bool(RELEASE_NAME),RELEASE_NAME)
 q="Could the Maple Leafs realistically acquire Connor McDavid?"
 plan=plan_capability(q,"public");check("planner",getattr(plan,"route",None)=="public_nhl_organizational_plausibility",getattr(plan,"route",None))
 check("registered","public_nhl_organizational_plausibility" in SPECIALISTS)
 ans=execute_specialist("public_nhl_organizational_plausibility",SimpleNamespace(files_loaded=[]),q,mode="public") or {}
 text=ans.get("natural_language_response",""); dev=ans.get("developer",{}); state=dev.get("organizational_plausibility",{})
 check("composes_scenario",dev.get("transaction_scenario",{}).get("net_cap_charge_delta")==12_500_000,str(dev.get("transaction_scenario",{})))
 check("mechanics_indeterminate",state.get("mechanical_status")=="scenario_indeterminate" and state.get("status")=="indeterminate_mechanics_with_fit_context",str(state.get("status")))
 check("no_intent_invention","does not establish that either club wants or would accept" in text,text)
 check("not_probability","Plausibility is not a probability" in str(ans.get("known_limitations",[])),str(ans.get("known_limitations",[])))
 check("current_need_gap","verified_current_team_need" in str(dev.get("missing_or_limited",[])),str(dev.get("missing_or_limited",[])))
 check("counterparty_gap","verified_counterparty_willingness" in str(dev.get("missing_or_limited",[])),str(dev.get("missing_or_limited",[])))
 print(f"Overall status: {'PASS' if all(checks) else 'FAIL'}");return 0 if all(checks) else 1
if __name__=="__main__":raise SystemExit(main())
