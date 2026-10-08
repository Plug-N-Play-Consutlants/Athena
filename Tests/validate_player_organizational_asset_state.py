"""Acceptance validation for v0.7.5 player/organizational asset state."""
from __future__ import annotations
from pathlib import Path
import sys
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from Core.version import ATHENA_VERSION, RELEASE_NAME
from Knowledge.Assets.player_asset_state import resolve_player_asset_state
from Athena.intent_planner import plan_capability
from Athena.execution_registry import SPECIALISTS, execute_specialist

def main():
    checks=[]
    def check(name,ok,detail=""):
        checks.append(bool(ok)); print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    check("version",tuple(map(int,ATHENA_VERSION.split("."))) >= (0,7,5,0,0),ATHENA_VERSION)
    check("release",bool(RELEASE_NAME),RELEASE_NAME)
    matt=resolve_player_asset_state(player_entity_id="nhl.player.auston_matthews",as_of="2026-09-28")
    check("matthews_identity",matt.player_name=="Auston Matthews" and matt.team_id=="TOR" and matt.position=="C",str(matt.to_dict()))
    check("career_stage",matt.age==29 and matt.career_stage=="prime",f"{matt.age}/{matt.career_stage}")
    check("contract_composed",matt.aav==13_250_000 and matt.contract_status=="canonical_active_contract",str(matt.aav))
    check("stats_composed",matt.production_authority=="canonical_statistical_evidence",matt.production_authority)
    check("no_opaque_market_value",not matt.evidence_complete_for_market_valuation and "market_or_acquisition_cost_evidence" in matt.missing_dimensions,str(matt.missing_dimensions))
    crosby=resolve_player_asset_state(player_entity_id="nhl.player.sidney_crosby",as_of="2026-09-28")
    check("missing_contract_not_unsigned",crosby.contract_status=="contract_evidence_unavailable" and "professional_contract_control" in crosby.missing_dimensions,crosby.contract_status)
    plan=plan_capability("What kind of organizational asset is Auston Matthews to Toronto?","public")
    check("athena_plans_asset_state",getattr(plan,"route",None)=="public_nhl_player_asset_state",getattr(plan,"route",None))
    check("registered","public_nhl_player_asset_state" in SPECIALISTS)
    ans=execute_specialist("public_nhl_player_asset_state",SimpleNamespace(files_loaded=[]),"What kind of organizational asset is Auston Matthews to Toronto?",mode="public")
    text=(ans or {}).get("natural_language_response","")
    check("athena_consumes_asset_state","29-year-old C" in text and "$13.25M AAV" in text,text)
    check("no_trade_score","unsupported trade-value score" in text,text)
    dev=(ans or {}).get("developer",{})
    check("asset_state_visible","player_asset_state" in dev,str(dev.keys()))
    print(f"Overall status: {'PASS' if all(checks) else 'FAIL'}")
    return 0 if all(checks) else 1
if __name__=="__main__":raise SystemExit(main())
