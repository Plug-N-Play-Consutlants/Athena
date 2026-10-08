"""Evidence-bounded organizational environment and plausibility reasoning."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any, Dict, Tuple

@dataclass(frozen=True)
class OrganizationalPlausibility:
    team_id:str
    team_name:str
    player_entity_id:str
    player_name:str
    as_of:str
    scenario_type:str
    status:str
    mechanical_status:str
    organizational_context_status:str
    fit_considerations:Tuple[str,...]
    friction_considerations:Tuple[str,...]
    established_facts:Tuple[str,...]
    hypotheses:Tuple[str,...]
    unresolved_inputs:Tuple[str,...]
    limitations:Tuple[str,...]
    explanation:str
    def to_dict(self)->Dict[str,Any]:
        d=asdict(self)
        for k in ("fit_considerations","friction_considerations","established_facts","hypotheses","unresolved_inputs","limitations"): d[k]=list(d[k])
        return d

def assess_organizational_plausibility(*,team_profile:Any,team_state:Any,player_asset_state:Any,scenario:Any)->OrganizationalPlausibility:
    """Compose existing authorities; never infer actual club intent from fit."""
    facts=[]; fit=[]; friction=[]; hypotheses=[]; unresolved=[]
    team_name=str(getattr(team_profile,"display_name",None) or team_state.team_name)
    facts.append(f"{team_name} is the organization represented by the canonical team state.")
    facts.append(f"{player_asset_state.player_name} is a {player_asset_state.age}-year-old {player_asset_state.position} in the {player_asset_state.career_stage.replace('_',' ')} career stage.")
    if player_asset_state.aav is not None:
        facts.append(f"Canonical contract evidence carries a ${player_asset_state.aav/1_000_000:.2f}M AAV through {player_asset_state.effective_to}.")
        friction.append(f"Any acquisition must account for the evidenced ${player_asset_state.aav/1_000_000:.2f}M AAV before additional transaction components.")
    if player_asset_state.production_authority=="canonical_statistical_evidence":
        fit.append("Canonical NHL statistical evidence is available for the player, so hockey-value investigation can proceed from observed production rather than reputation alone.")
    else: unresolved.append("canonical_statistical_evidence")
    strengths=list(getattr(team_profile,"strengths",[]) or [])
    risks=list(getattr(team_profile,"risks",[]) or [])
    if strengths: facts.append("Seed organizational profile strengths: "+", ".join(str(x) for x in strengths)+".")
    if risks:
        hypotheses.append("Potential fit should be tested against documented profile risks: "+", ".join(str(x) for x in risks)+".")
    if getattr(scenario,"net_cap_charge_delta",None) is not None:
        facts.append(f"The hypothetical contract-cap delta is ${scenario.net_cap_charge_delta/1_000_000:+.2f}M.")
    mechanical=str(getattr(scenario,"status","scenario_unavailable"))
    if mechanical!="scenario_evaluated":
        unresolved.extend(list(getattr(scenario,"unresolved_inputs",()) or ()))
        friction.append("Mechanical/cap feasibility is not established because the scenario ledger remains incomplete.")
    unresolved.extend(list(getattr(player_asset_state,"missing_dimensions",()) or ()))
    # Organizational profile can establish context, never current front-office desire.
    unresolved.extend(["verified_current_team_need","verified_counterparty_willingness","verified_acquisition_price"])
    hypotheses.append("Roster fit, competitive-window fit and acquisition appetite remain hypotheses until current roster/deployment and transaction-market evidence are attached.")
    status="bounded_plausibility_only"
    if mechanical=="scenario_evaluated" and not unresolved: status="evidence_supported_plausible"
    elif mechanical!="scenario_evaluated": status="indeterminate_mechanics_with_fit_context"
    limitations=(
        "Organizational fit is not evidence of front-office intent.",
        "Seed organizational profiles provide context but do not establish a current roster need, asking price, or willingness to transact.",
        "Plausibility is not a probability and is not a trade-value score.",
    )
    explanation=(f"Athena can identify evidence-backed considerations for {team_name} and {player_asset_state.player_name}, "
                 f"but the scenario is {status.replace('_',' ')}. "
                 + ("The transaction's cap mechanics are not fully determined from the current canonical ledger. " if mechanical!="scenario_evaluated" else "The supplied scenario mechanics are executable. ")
                 + "Organizational context can frame what to investigate; it does not establish that either club wants or would accept the transaction.")
    return OrganizationalPlausibility(team_state.team_id,team_name,player_asset_state.player_entity_id,player_asset_state.player_name,
        team_state.as_of,"player_acquisition",status,mechanical,"seed_profile_context",
        tuple(dict.fromkeys(fit)),tuple(dict.fromkeys(friction)),tuple(dict.fromkeys(facts)),tuple(dict.fromkeys(hypotheses)),
        tuple(dict.fromkeys(unresolved)),limitations,explanation)
