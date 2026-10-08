"""Contextual organizational significance: why an asset matters to this decision-maker."""
from __future__ import annotations
from typing import Any, Dict
from .asset_significance import assess_asset_significance


def assess_organizational_significance(asset:Dict[str,Any],*,organization:str="",competitive_horizon:str="unresolved",roster_context:Dict[str,Any]|None=None)->Dict[str,Any]:
    base=asset.get("asset_significance") if isinstance(asset.get("asset_significance"),dict) else assess_asset_significance(asset)
    considerations=[]
    dims={d["dimension"]:d for d in base.get("dimensions",[]) if isinstance(d,dict)}
    pedigree=dims.get("pedigree_rarity",{})
    age=dims.get("age_development_horizon",{})
    control=dims.get("contract_control_horizon",{})
    if pedigree.get("state")=="established":considerations.append(pedigree.get("significance"))
    if age.get("state")=="established":considerations.append(age.get("significance"))
    if control.get("state")=="established":considerations.append("Established organizational control preserves multiple strategic uses until the exact control horizon/restrictions say otherwise.")
    intelligence=base.get("player_intelligence") or {}
    pathway=intelligence.get("development_pathway") or {}
    events=pathway.get("events") or []
    if events:
        leagues=list(dict.fromkeys(str(e.get("league")) for e in events if isinstance(e,dict) and e.get("league")))
        if leagues:
            considerations.append("Observed career pathway includes " + ", ".join(leagues) +
                "; progression across levels informs the development profile, but does not establish why any promotion was delayed.")
    elif intelligence.get("uncertainty"):
        considerations.append("Longitudinal pathway evidence is incomplete; development speed and ceiling cannot be inferred from age alone.")
    if competitive_horizon=="unresolved":considerations.append("The organization's verified competitive horizon is unresolved, so Athena does not assume win-now or rebuild intent.")
    return {"asset":base.get("asset"),"organization":organization,"competitive_horizon":competitive_horizon,
            "considerations":[x for x in considerations if x],"replacement_cost_state":"bounded_inference",
            "opportunity_cost_state":"bounded_inference","summary":" ".join(x for x in considerations if x)}
