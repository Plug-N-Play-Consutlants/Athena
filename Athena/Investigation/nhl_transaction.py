"""Whole-picture NHL transaction investigation.

Acquire facts from registered authorities, infer fit from those facts, construct
possibilities, label uncertainty, and never convert fit into claimed club intent.
"""
from __future__ import annotations
from typing import Any, Dict, Iterable, List
from Athena.Investigation.state import InvestigationState
from Knowledge.Assets.organizational_rights_state import attach_rights_states, transaction_eligible
from Reasoning.Significance import assess_asset_significance, assess_organizational_significance, significance_sort_key
from Reasoning.Decisions import assess_transaction_decision


def _candidate_signals(player:Dict[str,Any])->List[str]:
    s=[];age=player.get("age");pos=str(player.get("position") or "");pts=player.get("points");gp=player.get("games_played")
    draft=player.get("draft") if isinstance(player.get("draft"),dict) else {}
    overall=draft.get("overall_pick")
    if isinstance(overall,int):
        if overall==1:s.append("first-overall draft pedigree")
        elif overall<=5:s.append("top-five draft pedigree")
        elif overall<=15:s.append("high first-round draft pedigree")
        elif overall<=32:s.append("first-round draft pedigree")
    if isinstance(age,int):
        if age<=23:s.append("young/development upside")
        elif age<=27:s.append("prime-age profile")
        elif age>=31:s.append("veteran age profile")
    if pos:s.append(f"position {pos}")
    if player.get("shoots_catches"):s.append(f"shoots/catches {player['shoots_catches']}")
    if isinstance(pts,(int,float)) and isinstance(gp,(int,float)) and gp>0:
        rate=pts/gp
        if rate>=.8:s.append("high current scoring production")
        elif rate>=.5:s.append("meaningful current scoring production")
    if player.get("avg_toi"):s.append("evidenced NHL deployment")
    return s


def _priority(player:Dict[str,Any])->tuple:
    """Evidence-driven investigation priority, explicitly not a trade-value score."""
    age=player.get("age") if isinstance(player.get("age"),int) else 99
    pts=player.get("points") if isinstance(player.get("points"),(int,float)) else -1
    draft=player.get("draft") if isinstance(player.get("draft"),dict) else {}
    overall=draft.get("overall_pick") if isinstance(draft.get("overall_pick"),int) else 999
    draft_weight=0
    if overall==1:draft_weight=12
    elif overall<=5:draft_weight=9
    elif overall<=15:draft_weight=6
    elif overall<=32:draft_weight=3
    development=4 if age<=23 else 2 if age<=27 else 0
    production=4 if pts>=50 else 2 if pts>=25 else 0
    relationship=2 if player.get("relationship")=="prospect" else 1
    return (draft_weight+development+production+relationship, -overall, pts, -age)


def _candidate_pool(org:Dict[str,Any],protected:Iterable[str],limit:int=8)->List[Dict[str,Any]]:
    protected_cf={str(x).casefold() for x in protected}
    rows=[];seen=set()
    for p in list(org.get("roster") or [])+list(org.get("prospects") or []):
        name=str(p.get("name") or "");pid=str(p.get("nhl_player_id") or "")
        if not name or name.casefold() in protected_cf or any(x and x in name.casefold() for x in protected_cf):continue
        key=pid or name.casefold()
        if key in seen:continue
        seen.add(key);rows.append(dict(p))
    rows.sort(key=_priority,reverse=True)
    return rows[:limit]


def _landing_draft(payload:Any)->Dict[str,Any]:
    if not isinstance(payload,dict):return {}
    d=payload.get("draftDetails") if isinstance(payload.get("draftDetails"),dict) else {}
    def integer(v):
        try:return int(v) if v is not None else None
        except (TypeError,ValueError):return None
    return {"year":integer(d.get("year")),"round":integer(d.get("round")),"pick_in_round":integer(d.get("pickInRound")),"overall_pick":integer(d.get("overallPick")),"team_abbrev":str(d.get("teamAbbrev") or "")}


def _enrich_candidates(candidates:List[Dict[str,Any]],client:Any,inv:InvestigationState)->None:
    """Escalate material candidates from broad discovery into player-level evidence."""
    inv.consider("nhl.player_landing")
    successes=0
    for asset in candidates:
        pid=str(asset.get("nhl_player_id") or "")
        if not pid:continue
        try:
            landing=client.get_player_landing(pid)
        except Exception as exc:
            asset.setdefault("enrichment_errors",[]).append(f"player_landing: {type(exc).__name__}: {exc}")
            continue
        successes+=1
        asset["draft"]=_landing_draft(landing)
        asset["current_team_abbrev"]=str(landing.get("currentTeamAbbrev") or asset.get("team") or "") if isinstance(landing,dict) else str(asset.get("team") or "")
        asset["player_landing_acquired"]=True
    if successes:inv.executed("nhl.player_landing")


def _fit_and_cost(asset:Dict[str,Any],seller_roster:List[Dict[str,Any]])->None:
    pos=str(asset.get("position") or "");peers=[x for x in seller_roster if str(x.get("position") or "")==pos]
    fit=[];cost=[];draft=asset.get("draft") if isinstance(asset.get("draft"),dict) else {};overall=draft.get("overall_pick")
    if overall==1:
        fit.append("first-overall pedigree materially raises the upside and centerpiece potential of the asset")
        cost.append("moving a first-overall organizational asset carries unusually high future-value and market-pressure cost")
    elif isinstance(overall,int) and overall<=15:
        fit.append(f"No. {overall} overall draft pedigree adds high-end development upside")
        cost.append("Toronto would be surrendering a premium drafted asset with meaningful upside")
    elif asset.get("relationship")=="prospect":fit.append("adds development/upside rather than only present roster value")
    if isinstance(asset.get("age"),int) and asset["age"]<=24:
        fit.append("adds a young controllable-age asset profile")
        cost.append("Toronto would be surrendering youth/upside")
    if asset.get("shoots_catches"):
        handed=str(asset["shoots_catches"]);same=sum(1 for x in peers if str(x.get("shoots_catches") or "")==handed)
        fit.append(f"{handed}-shot option at {pos}; seller currently shows {same} same-handed roster peer(s) in NHL evidence")
    if isinstance(asset.get("points"),(int,float)):
        fit.append(f"brings evidenced NHL production ({asset['points']} current-period points in the club-stats payload)")
        cost.append("removes evidenced NHL production from Toronto")
    if asset.get("avg_toi"):cost.append("removes a player with evidenced NHL deployment")
    if not fit:fit.append("asset belongs in the fit test because it is a current non-protected organizational asset")
    if not cost:cost.append("Toronto must compare the asset's replacement cost against the upgrade created by the target")
    asset["fit_signals"]=_candidate_signals(asset);asset["seller_fit_considerations"]=fit;asset["buyer_cost_considerations"]=cost


def _construct_package(candidates:List[Dict[str,Any]],target_name:str)->Dict[str,Any]:
    ranked=sorted(candidates,key=significance_sort_key,reverse=True)
    # A named package is an analytical construction, not a claim of sufficient market value.
    core=ranked[:3]
    names=[str(x.get("name") or "") for x in core if str(x.get("name") or "")]
    return {"target":target_name,"assets":names,"asset_count":len(names),"status":"constructed_from_current_evidence" if names else "unavailable",
            "assessment":"This is the strongest named player/prospect construction Athena can support from the currently acquired evidence; it is not a claim that the seller would accept it or that no rival can offer more."}


def investigate_nhl_transaction(*,inquiry:Any,buyer_abbrev:str,target_team_abbrev:str,target_name:str)->InvestigationState:
    from Knowledge.Organizations.nhl_roster_evidence import acquire_team_player_evidence
    from Providers.NHL.nhl_client import NHLClient
    inv=InvestigationState(inquiry=inquiry.to_dict() if hasattr(inquiry,"to_dict") else dict(inquiry or {}));inv.passes=1
    inv.require(*getattr(inquiry,"evidence_requirements",[]),"buyer_current_roster","buyer_prospects","seller_current_roster","seller_prospects","organizational_fit","candidate_enrichment","organizational_control","transaction_eligibility","comparative_asset_analysis","named_package","package_evaluation","acquisition_price")
    if "salary_cap" in getattr(inquiry,"constraints_waived",[]):inv.mark("cap_cba_state","waived",note="User explicitly waived salary-cap feasibility for this scenario.")
    for cap in ("nhl.current_roster","nhl.prospects","nhl.club_stats_current","nhl.player_landing","asset_state","organizational_fit","transaction_construction"):inv.consider(cap)
    client=NHLClient();buyer=acquire_team_player_evidence(buyer_abbrev,client=client);seller=acquire_team_player_evidence(target_team_abbrev,client=client)
    inv.executed("nhl.current_roster");inv.executed("nhl.prospects");inv.executed("nhl.club_stats_current")
    inv.evidence["buyer_organization"]=buyer;inv.evidence["seller_organization"]=seller
    for prefix,org in (("buyer",buyer),("seller",seller)):
        r=len(org.get("roster") or []);p=len(org.get("prospects") or []);errs=org.get("acquisition_errors") or []
        inv.mark(f"{prefix}_current_roster","acquired_from_provider" if r else "unresolved_after_investigation",provider="NHL.com",capability="current_roster",evidence=f"{r} normalized roster players",note="; ".join(errs))
        inv.mark(f"{prefix}_prospects","acquired_from_provider" if p else "partial",provider="NHL.com",capability="prospects",evidence=f"{p} normalized prospect records",note="; ".join(errs))
    candidates=_candidate_pool(buyer,getattr(inquiry,"protected_assets",[]))
    # Provider relationship and legal/control state are separate concepts. Attach
    # an explicit rights state before any player can enter a construction.
    candidates=attach_rights_states(candidates,buyer_abbrev.upper())
    eligible=[x for x in candidates if transaction_eligible(x)]
    excluded=[x for x in candidates if not transaction_eligible(x)]
    inv.evidence["control_excluded_assets"]=[{"name":x.get("name"),"rights_state":x.get("rights_state")} for x in excluded]
    candidates=eligible
    _enrich_candidates(candidates,client,inv)
    seller_roster=list(seller.get("roster") or [])
    for asset in candidates:
        asset["asset_significance"]=assess_asset_significance(asset)
        asset["organizational_significance"]=assess_organizational_significance(asset,organization="Toronto Maple Leafs")
        _fit_and_cost(asset,seller_roster)
    candidates.sort(key=significance_sort_key,reverse=True)
    inv.evidence["candidate_assets"]=candidates;inv.executed("asset_state")
    controlled=sum(1 for x in candidates if (x.get("rights_state") or {}).get("control_status")=="controlled")
    inv.mark("organizational_control","acquired_from_provider" if controlled else "unresolved_after_investigation",provider="NHL.com",capability="organizational_rights_state",evidence=f"{controlled} candidate assets have current organizational-control evidence")
    inv.mark("transaction_eligibility","partial" if candidates else "unresolved_after_investigation",provider="NHL.com",capability="organizational_rights_state",evidence=f"{len(candidates)} controlled assets are eligible for transaction analysis",note="Exact SPC/rights mechanism and restrictions remain evidence-dependent; playing location alone is never treated as ownership.")
    enriched=sum(1 for x in candidates if x.get("player_landing_acquired"))
    inv.mark("candidate_enrichment","acquired_from_provider" if enriched else "partial",provider="NHL.com",capability="player_landing",evidence=f"{enriched}/{len(candidates)} candidate player landings acquired")
    if candidates:
        inv.findings.append(f"Athena identified and comparatively examined {len(candidates)} non-protected Toronto roster/prospect assets from current NHL evidence.")
        inv.mark("transaction_components","partial",capability="asset_state",evidence="named non-protected candidate pool")
        inv.mark("comparative_asset_analysis","requires_analytical_inference",capability="asset_state",evidence="candidate pool ranked for investigation using draft pedigree, age/development state and evidenced current production")
    else:
        inv.mark("transaction_components","unresolved_after_investigation",capability="asset_state",note="NHL acquisition produced no usable non-protected candidate pool.")
        inv.mark("comparative_asset_analysis","unresolved_after_investigation",capability="asset_state",note="No candidate assets were available to compare.")
    inv.executed("organizational_fit");inv.mark("organizational_fit","requires_analytical_inference",capability="organizational_fit",note="Fit is an Athena conclusion from roster/player evidence, not a claim of front-office intent.")
    # Explicit user-named outgoing assets define the scenario. Do not silently
    # optimize them into Athena's preferred package. Resolved subjects other than
    # the target and protected assets are treated as scenario-locked components.
    protected_cf={str(x).casefold() for x in getattr(inquiry,"protected_assets",[])}
    target_cf=str(target_name or "").casefold()
    requested_names=[str(x).strip() for x in getattr(inquiry,"named_outgoing_assets",[]) if str(x).strip()]
    if not requested_names:
        for subject in getattr(inquiry,"subjects",[]):
            name=str(subject or "").strip(); cf=name.casefold()
            if not name or cf==target_cf or cf in protected_cf or any(p and (p==cf or p in cf) for p in protected_cf): continue
            if name not in requested_names: requested_names.append(name)
    by_name={str(x.get("name") or "").casefold():x for x in candidates}
    requested_assets=[by_name[n.casefold()] for n in requested_names if n.casefold() in by_name]
    if requested_names:
        package={"target":target_name,"assets":[str(x.get("name") or "") for x in requested_assets],"asset_count":len(requested_assets),
                 "status":"scenario_locked" if len(requested_assets)==len(requested_names) else "scenario_locked_partial_evidence",
                 "requested_assets":requested_names,"unresolved_requested_assets":[n for n in requested_names if n.casefold() not in by_name],
                 "assessment":"This is the user's named outgoing package. Athena may evaluate it but may not substitute different assets unless the user asks for a stronger or alternative construction."}
    else:
        package=_construct_package(candidates,target_name)
    inv.evidence["named_package"]=package;inv.executed("transaction_construction")
    if package["status"] in {"constructed_from_current_evidence","scenario_locked","scenario_locked_partial_evidence"}:
        evaluated_assets=requested_assets if requested_names else candidates[:3]
        firsts=sum(1 for x in evaluated_assets if ((x.get("draft") or {}).get("overall_pick")==1))
        premium=sum(1 for x in evaluated_assets if isinstance((x.get("draft") or {}).get("overall_pick"),int) and (x.get("draft") or {}).get("overall_pick")<=32)
        if firsts and premium>=2:
            verdict="serious_foundation_but_sufficiency_unproven"
            conclusion=f"The construction has a legitimate centerpiece and secondary premium prospect value, but Athena cannot defend it as sufficient for {target_name} without complete draft-capital, contract/control and comparative seller-alternative evidence."
        else:
            verdict="insufficiently_supported"
            conclusion=f"Athena can construct a controlled-asset offer, but current evidence does not support calling it sufficient for {target_name}."
        package["evaluation"]={"verdict":verdict,"conclusion":conclusion,"draft_capital_status":"not_acquired_on_this_path","seller_alternatives_status":"not_comprehensively_acquired"}
        inv.mark("package_evaluation","requires_analytical_inference",capability="transaction_construction",evidence=verdict,note=conclusion)
        inv.findings.append(conclusion)
        inv.mark("named_package","requires_analytical_inference",capability="transaction_construction",evidence=", ".join(package["assets"]),note=package["assessment"])
        inv.findings.append(f"Athena completed a strongest-current-evidence named construction for {target_name}: {', '.join(package['assets'])}.")
    else:
        inv.mark("package_evaluation","unresolved_after_investigation",capability="transaction_construction",note="No named package exists to evaluate.")
        inv.mark("named_package","unresolved_after_investigation",capability="transaction_construction",note="No evidence-backed named construction could be produced.")
    inv.mark("acquisition_price","requires_analytical_inference",capability="transaction_construction",note=f"No authoritative source can define a hypothetical sufficient price for {target_name}; Athena must compare package quality and alternatives and label uncertainty.")
    # Produce a study contract for Scout. These are analytical dimensions, not a
    # fixed presentation template; Scout may omit sections that lack material evidence.
    evaluation=package.get("evaluation") if isinstance(package.get("evaluation"),dict) else {}
    cap_waived="salary_cap" in getattr(inquiry,"constraints_waived",[])
    raw_question=str(getattr(inquiry,"raw_question","") or "")
    asks_decision=any(token in raw_question.casefold() for token in ("would you do it", "would you make", "if you were running", "should toronto", "should the leafs", "should they do it"))
    rq_cf=raw_question.casefold()
    availability_assumed=bool(requested_names) and any(token in rq_cf for token in ("could acquire", "could get", "if the leafs could", "if toronto could"))
    decision=""
    package_assets=[x for x in candidates if str(x.get("name") or "") in set(package.get("assets") or [])]
    decision_quality=assess_transaction_decision(target_name=target_name,outgoing_assets=package_assets,
        protected_assets=getattr(inquiry,"protected_assets",[]),seller_name="the seller",
        mechanics_status="waived_for_scenario" if cap_waived else "unresolved",
        rules_status="bounded_effective_rules",seller_alternatives_known=False,availability_assumed=availability_assumed) if package_assets else {}
    if asks_decision and package.get("status") in {"constructed_from_current_evidence","scenario_locked","scenario_locked_partial_evidence"}:
        decision=str(decision_quality.get("verdict") or "")
    inv.evidence["decision_quality"]=decision_quality
    inv.evidence["analytical_study"]={
        "question":raw_question,
        "thesis":str(evaluation.get("conclusion") or package.get("assessment") or ""),
        "scenario_locked":bool(requested_names),
        "availability_assumed_by_user":availability_assumed,
        "decision_requested":asks_decision,
        "buyer_decision":decision,
        "competitive_objective":"Improve the organization's ability to achieve competitive success within governing rules and the relevant competitive horizon.",
        "assets_on_table":[str(x.get("name") or "") for x in candidates[:5] if str(x.get("name") or "")],
        "proposed_construction":dict(package),
        "buyer_objective":f"Toronto is testing whether the proven present impact of {target_name} is worth surrendering a package led by premium future/upside assets while preserving the user's protected assets.",
        "seller_objective":f"The seller gives up {target_name}, so the return must create enough future/control upside to compete with keeping the player or choosing a stronger rival offer; current evidence does not establish that threshold.",
        "financial_status":"waived_for_scenario" if cap_waived else "execute_registered_cap_cba_reasoning",
        "rules_status":"preserve known transaction restrictions; unresolved restrictions remain qualifications rather than invented facts",
        "material_unresolved":["complete draft-capital evidence","exact contract/control restrictions","comparative seller alternatives"],
        "decision_quality":decision_quality,
        "presentation_contract":"analytical_study_v2",
    }
    inv.mark("analytical_study","requires_analytical_inference",capability="analytical_study",evidence="study dimensions composed from completed investigation")
    if buyer.get("acquisition_errors") or seller.get("acquisition_errors"):inv.uncertainties.append("One or more NHL evidence calls failed; conclusions must be bounded to evidence actually acquired.")
    # Saturation is only legal after comparative analysis and a construction attempt.
    inv.passes=4;inv.saturated=bool(candidates and package["status"]=="constructed_from_current_evidence" and package.get("evaluation"))
    return inv
