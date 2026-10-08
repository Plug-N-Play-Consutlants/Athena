"""Canonical player intelligence.

Facts, comparative baselines, causal explanations and projections are deliberately
separate.  A short NHL sample can be statistically immature while roster/deployment
facts remain meaningful contextual evidence.
"""
from __future__ import annotations
from typing import Any,Dict,List
from Reasoning.models.player_intelligence import PlayerIntelligence

def _known(v): return v is not None and v!="" and v!=[] and v!={}

def build_player_intelligence(player:Dict[str,Any], *, history:List[Dict[str,Any]]|None=None,
                              baselines:List[Dict[str,Any]]|None=None,
                              opportunity:Dict[str,Any]|None=None)->Dict[str,Any]:
    history=list(history or player.get("development_history") or [])
    baselines=list(baselines or player.get("comparative_baselines") or [])
    opportunity=dict(opportunity or player.get("opportunity_context") or {})
    draft=player.get("draft") if isinstance(player.get("draft"),dict) else {}
    gp=player.get("games_played") if isinstance(player.get("games_played"),(int,float)) else None
    age=player.get("age") if isinstance(player.get("age"),(int,float)) else None
    evidence={k:player.get(k) for k in ("age","position","games_played","goals","assists","points","avg_toi","relationship") if _known(player.get(k))}
    if draft:evidence["draft"]=draft
    if history:evidence["development_history"]=history
    pathway={"state":"established" if history else "unresolved","events":history,
             "principle":"Elapsed time is not developmental delay; pathway choices and causes require their own evidence."}
    sample={"statistical_sample":"immature" if gp is not None and gp<20 else "developing" if gp is not None and gp<82 else "established" if gp is not None else "unresolved",
            "contextual_evidence":"available" if any(_known(player.get(k)) for k in ("relationship","avg_toi","position")) or history else "limited"}
    impact={"state":"bounded_inference" if gp else "unresolved","sample_sufficiency":sample,"dimensions":{}}
    if gp:
        for k in ("goals","assists","points","avg_toi"):
            if _known(player.get(k)): impact["dimensions"][k]=player.get(k)
    trajectory_state="unresolved"
    trajectory_reason="Development trajectory requires longitudinal pathway evidence; age alone is not a trajectory."
    if history:
        trajectory_state="supported_inference"
        trajectory_reason="Longitudinal level/role evidence is available for trajectory assessment; causal explanations remain separate unless evidenced."
    trajectory={"state":trajectory_state,"reason":trajectory_reason,"age":age,"comparative_baselines":baselines,
                "causal_explanations":"unresolved" if not opportunity.get("established_causes") else opportunity.get("established_causes")}
    projection={"state":"bounded_inference" if (history or gp) else "unresolved",
                "method":"update prior development evidence with increasingly representative NHL evidence",
                "range_not_declaration":True,"confidence":"low" if not gp or gp<20 else "developing",
                "change_triggers":["larger NHL sample","role/deployment change","level transition","new comparative baseline","injury/availability change"]}
    uncertainty=[]
    if not baselines: uncertainty.append("Relevant full-population comparison cohorts are not yet established; non-attainers must remain in development baselines.")
    if not history: uncertainty.append("Longitudinal amateur/NCAA/AHL/NHL pathway evidence is incomplete on this path.")
    if not opportunity: uncertainty.append("Roster opportunity, coaching/system fit and promotion constraints are unresolved.")
    return PlayerIntelligence(str(player.get("name") or ""),evidence,pathway,baselines,opportunity,trajectory,impact,projection,uncertainty).to_dict()
