"""Acceptance validation for v0.7.1 canonical NHL contract evidence."""
from __future__ import annotations
from pathlib import Path
import sys
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from Core.version import ATHENA_VERSION, RELEASE_NAME
from Knowledge.Contracts.player_contract_state import resolve_player_contract_state
from Athena.intent_planner import plan_capability
from Athena.execution_registry import SPECIALISTS, execute_specialist

def main():
    checks=[]
    def check(name,ok,detail=""):
        checks.append(bool(ok)); print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    check("version", tuple(map(int, ATHENA_VERSION.split("."))) >= (0,7,1,0,0), ATHENA_VERSION)
    check("release", bool(RELEASE_NAME), RELEASE_NAME)
    mcd=resolve_player_contract_state(player_entity_id="nhl.player.connor_mcdavid",as_of="2026-09-28")
    check("mcdavid_contract",mcd.aav==12_500_000 and mcd.term_years==2 and mcd.team_id=="nhl.team.edm",str(mcd.to_dict()))
    check("effective_date",mcd.active_on("2026-09-28") and not mcd.active_on("2026-06-30"))
    check("cap_share",round(mcd.cap_share("2026-09-28")*100,2)==12.02,str(mcd.cap_share("2026-09-28")))
    matt=resolve_player_contract_state(player_entity_id="nhl.player.auston_matthews",as_of="2026-09-28")
    check("matthews_contract",matt.aav==13_250_000 and matt.effective_to=="2028-06-30")
    check("fantasy_separation","Fantrax" not in str(mcd.to_dict()) and "fantasy" not in str(mcd.to_dict()).lower())
    plan=plan_capability("What is Connor McDavid's contract and cap hit?","public")
    check("athena_plans_contract",getattr(plan,"route",None)=="public_nhl_player_contract",getattr(plan,"route",None))
    check("registered","public_nhl_player_contract" in SPECIALISTS)
    ans=execute_specialist("public_nhl_player_contract",SimpleNamespace(files_loaded=[]),"What is Connor McDavid's contract and cap hit?",mode="public")
    text=(ans or {}).get("natural_language_response","")
    check("athena_consumes_contract","$12.50M AAV" in text and "12.02%" in text,text)
    check("no_team_ledger_claim","not the club's total cap usage" in text.lower(),text)
    missing=(ans or {}).get("developer",{}).get("missing_or_limited",[])
    check("spc_limit_explicit","complete_registered_spc" in str((ans or {}).get("developer",{})),str(missing))
    print(f"Overall status: {'PASS' if all(checks) else 'FAIL'}")
    return 0 if all(checks) else 1
if __name__=="__main__": raise SystemExit(main())
