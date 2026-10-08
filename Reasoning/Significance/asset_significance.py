"""Evidence-bounded asset significance.

Significance interprets established evidence; it is not a universal trade-value score.
Missing dimensions remain unresolved and do not silently become negative evidence.
"""
from __future__ import annotations
from typing import Any, Dict, List, Tuple
from Reasoning.Players import build_player_intelligence


def _dimension(name:str,state:str,significance:str,evidence:Any=None,weight:int=0)->Dict[str,Any]:
    return {"dimension":name,"state":state,"significance":significance,"evidence":evidence,"ordering_weight":weight}


def assess_asset_significance(asset:Dict[str,Any])->Dict[str,Any]:
    dims:List[Dict[str,Any]]=[]
    player_intelligence=asset.get("player_intelligence") if isinstance(asset.get("player_intelligence"),dict) else build_player_intelligence(asset)
    asset["player_intelligence"]=player_intelligence
    draft=asset.get("draft") if isinstance(asset.get("draft"),dict) else {}
    overall=draft.get("overall_pick") if isinstance(draft.get("overall_pick"),int) else None
    if overall is not None:
        if overall==1:
            dims.append(_dimension("pedigree_rarity","established","First-overall pedigree is a rare acquisition-cost signal and materially raises the opportunity cost of surrendering the asset.",overall,12))
        elif overall<=5:
            dims.append(_dimension("pedigree_rarity","established",f"No. {overall} overall pedigree supplies uncommon high-end development optionality.",overall,9))
        elif overall<=15:
            dims.append(_dimension("pedigree_rarity","established",f"No. {overall} overall pedigree supports meaningful high-end development value.",overall,6))
        elif overall<=32:
            dims.append(_dimension("pedigree_rarity","established",f"First-round pedigree supports above-baseline development value, but does not by itself establish elite outcome probability.",overall,3))
        else:
            dims.append(_dimension("pedigree_rarity","established",f"Draft position No. {overall} is established but is not treated as premium pedigree by itself.",overall,0))
    else:
        dims.append(_dimension("pedigree_rarity","unresolved","Draft pedigree is not established on this evidence path."))
    age=asset.get("age") if isinstance(asset.get("age"),int) else None
    if age is not None:
        if age<=20: text="The asset is early in its development horizon, preserving substantial growth time and organizational optionality."; w=6
        elif age<=23: text="The asset remains in a young development horizon with meaningful runway before a mature performance baseline."; w=5
        elif age<=27: text="The asset is in or approaching prime-age seasons, shifting significance toward present contribution."; w=3
        else: text="The asset's age makes present utility more important than long development optionality."; w=1
        dims.append(_dimension("age_development_horizon","established",text,age,w))
    else:dims.append(_dimension("age_development_horizon","unresolved","Age/development horizon is not established."))
    pts=asset.get("points");gp=asset.get("games_played")
    if isinstance(pts,(int,float)) and isinstance(gp,(int,float)) and gp>0:
        rate=pts/gp
        text=f"Observed production is {pts} points in {gp} games ({rate:.2f} points/game); this is current performance evidence, not a complete projection."
        dims.append(_dimension("current_performance_trajectory","established",text,{"points":pts,"games_played":gp,"points_per_game":round(rate,3)},min(5,max(1,int(rate*5)))))
    else:dims.append(_dimension("current_performance_trajectory","unresolved","Comparable current performance/trajectory evidence is incomplete; Athena does not convert the absence into a negative evaluation."))
    rs=asset.get("rights_state") if isinstance(asset.get("rights_state"),dict) else {}
    if rs.get("control_status")=="controlled":
        status=str(rs.get("transaction_status") or "controlled")
        dims.append(_dimension("contract_control_horizon","established",f"Current organizational control is established ({status}); exact duration and restrictions still determine how much flexibility that control creates.",status,3))
    else:dims.append(_dimension("contract_control_horizon","unresolved","Current organizational control is not established strongly enough to assign control-horizon value."))
    pos=str(asset.get("position") or "").strip()
    if pos:dims.append(_dimension("positional_roster_significance","supported_inference",f"Position {pos} is established, but organizational scarcity/replacement difficulty requires roster-depth evidence before Athena can call the position unusually scarce.",pos,1))
    else:dims.append(_dimension("positional_roster_significance","unresolved","Position/role significance is incomplete."))
    dims.append(_dimension("replacement_cost","bounded_inference","Replacement cost can be inferred from rarity, development runway, control and performance, but a market-equivalent replacement is not established on this path."))
    dims.append(_dimension("alternative_uses","bounded_inference","A controlled asset can be retained for development or deployed in another transaction; specific competing opportunities require market evidence."))
    traj=player_intelligence.get("development_trajectory") or {}
    dims.append(_dimension("development_trajectory",str(traj.get("state") or "unresolved"),str(traj.get("reason") or "Development trajectory is unresolved."),traj,2 if traj.get("state")=="supported_inference" else 0))
    established=sum(1 for d in dims if d["state"] in {"established","supported_inference"})
    unresolved=sum(1 for d in dims if d["state"]=="unresolved")
    return {"asset":str(asset.get("name") or ""),"dimensions":dims,"established_dimensions":established,"unresolved_dimensions":unresolved,
            "ordering_weight":sum(int(d.get("ordering_weight") or 0) for d in dims),
            "summary":"; ".join(d["significance"] for d in dims if d["state"] in {"established","supported_inference"}),
            "player_intelligence":player_intelligence}


def significance_sort_key(asset:Dict[str,Any])->Tuple[int,int,int]:
    sig=asset.get("asset_significance") if isinstance(asset.get("asset_significance"),dict) else assess_asset_significance(asset)
    draft=asset.get("draft") if isinstance(asset.get("draft"),dict) else {}; overall=draft.get("overall_pick") if isinstance(draft.get("overall_pick"),int) else 999
    age=asset.get("age") if isinstance(asset.get("age"),int) else 99
    return (int(sig.get("ordering_weight") or 0),-overall,-age)
