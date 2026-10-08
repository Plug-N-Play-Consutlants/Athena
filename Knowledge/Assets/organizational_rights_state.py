"""Effective-dated organizational control and transferability state for NHL assets.

Playing location is not ownership. This layer records what evidence establishes
about an NHL organization's control of a player and what object could be moved.
It deliberately avoids inventing an SPC, rights expiry, or trade restriction
when the provider evidence does not establish one.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

@dataclass(frozen=True)
class OrganizationalRightsState:
    player_id:str
    player_name:str
    organization:str
    relationship:str
    control_status:str
    control_mechanism:str
    transferable_object:str
    transaction_status:str
    current_club_or_context:str=""
    effective_from:str=""
    effective_through:str=""
    restrictions:tuple[str,...]=()
    evidence:tuple[str,...]=()
    confidence:float=0.0
    def to_dict(self)->Dict[str,Any]: return asdict(self)


def resolve_provider_rights_state(player:Dict[str,Any], organization:str)->OrganizationalRightsState:
    """Resolve only what current NHL organizational provider evidence supports."""
    relationship=str(player.get("relationship") or "")
    name=str(player.get("name") or "")
    pid=str(player.get("nhl_player_id") or "")
    context=str(player.get("current_team_abbrev") or player.get("team") or "")
    if relationship=="current_roster":
        return OrganizationalRightsState(pid,name,organization,relationship,
            "controlled","current_nhl_roster_relationship","player_contract_or_registered_player_rights",
            "transaction_eligible_subject_to_restrictions",context,
            restrictions=("Exact SPC, NMC/NTC, retention and other CBA restrictions require contract evidence.",),
            evidence=("NHL current roster endpoint associates the player with the organization.",),confidence=.90)
    if relationship=="prospect":
        # A current provider association is evidence of an organizational/prospect
        # relationship, but it is not by itself proof that draft/contract rights
        # remain legally controlled on the as-of date. Historical draft rights can
        # expire while a provider record remains discoverable. Keep the association
        # useful without promoting it into a tradeable asset.
        return OrganizationalRightsState(pid,name,organization,relationship,
            "association_only","provider_prospect_association_unreconciled","none_established",
            "requires_current_rights_evidence",context,
            restrictions=("Current control mechanism and effective-through date must be established before transaction eligibility.",),
            evidence=("NHL prospects endpoint currently associates the player with the organization; this alone does not establish current legal control.",),confidence=.62)
    return OrganizationalRightsState(pid,name,organization,relationship,
        "not_established","unknown","none_established","not_eligible_without_control_evidence",context,
        restrictions=("Athena cannot offer an asset that the organization is not evidenced to control.",),confidence=.25)


def attach_rights_states(players:List[Dict[str,Any]], organization:str)->List[Dict[str,Any]]:
    out=[]
    for raw in players:
        p=dict(raw);p["rights_state"]=resolve_provider_rights_state(p,organization).to_dict();out.append(p)
    return out


def transaction_eligible(player:Dict[str,Any])->bool:
    state=player.get("rights_state") if isinstance(player.get("rights_state"),dict) else {}
    return str(state.get("control_status") or "") == "controlled" and str(state.get("transaction_status") or "").startswith(("transaction_eligible","rights_or_contract_potentially_transferable"))
