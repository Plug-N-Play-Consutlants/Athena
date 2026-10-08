from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from Core.version import ATHENA_VERSION
from Athena.Inquiry.state import build_inquiry_state, select_primary_player_subject
from Athena.intent_planner import plan_capability, _public_player_profiles_for

fail=[]
def check(name, ok, detail=""):
    print(("PASS" if ok else "FAIL")+f" | {name}"+(f" | {detail}" if detail else ""))
    if not ok: fail.append(name)

check("version", tuple(map(int, ATHENA_VERSION.split("."))) >= (0, 7, 7, 3, 4), ATHENA_VERSION)
q="Could the Maple Leafs realistically acquire Connor McDavid without trading Auston Matthews?"
i=build_inquiry_state(q,"public")
check("professional subjects persist", "Connor McDavid" in i.subjects and "Auston Matthews" in i.subjects, str(i.subjects))
check("protected asset", any("Matthews" in x for x in i.protected_assets), str(i.protected_assets))
p=select_primary_player_subject(q,_public_player_profiles_for(q))
check("transaction subject", getattr(p,"display_name","")=="Connor McDavid", getattr(p,"display_name",None))
check("plausibility route", plan_capability(q,"public").route=="public_nhl_organizational_plausibility", plan_capability(q,"public").route)
q2="Forget the salary cap for a moment. How could Toronto get McDavid without giving up Matthews?"
i2=build_inquiry_state(q2,"public")
check("cap waiver", "salary_cap" in i2.constraints_waived, str(i2.constraints_waived))
check("waiver removes enforced cap", "salary_cap" not in i2.constraints_enforced, str(i2.constraints_enforced))
check("waiver route", plan_capability(q2,"public").route=="public_nhl_transaction_scenario", plan_capability(q2,"public").route)
q3="Show me Auston Matthews over the last five seasons"
i3=build_inquiry_state(q3,"public")
check("five season scope", i3.temporal_scope.kind=="season_window" and i3.temporal_scope.value==5, str(i3.temporal_scope))
q4="Summarize what happened last week in my league"
i4=build_inquiry_state(q4,"fantasy")
check("fantasy period", i4.temporal_scope.label=="last week", str(i4.temporal_scope))
check("fantasy evidence requirements", all(x in i4.evidence_requirements for x in ["league_state","time_scoped_transactions","standings"]), str(i4.evidence_requirements))
if fail: raise SystemExit("FAILED: "+", ".join(fail))
