"""Canonical player/organizational asset state.

This object composes existing evidence authorities without assigning an opaque
trade-value score. It describes what Athena can establish about a player as an
organizational asset at a point in time and preserves gaps for later reasoning.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any, Dict, Tuple

def _age(born: str, as_of: date) -> int | None:
    try:
        birth=date.fromisoformat(str(born))
    except (TypeError, ValueError):
        return None
    return as_of.year-birth.year-((as_of.month,as_of.day)<(birth.month,birth.day))

def _career_stage(age: int | None) -> str:
    if age is None: return "unknown"
    if age <= 22: return "early_career"
    if age <= 26: return "prime_entry"
    if age <= 30: return "prime"
    if age <= 34: return "veteran"
    return "late_career_veteran"

@dataclass(frozen=True)
class PlayerAssetState:
    player_entity_id: str
    player_name: str
    as_of: str
    team_id: str
    team_name: str
    position: str
    age: int | None
    career_stage: str
    organizational_relationship: str
    contract_status: str
    contract_id: str
    aav: int | None
    effective_to: str
    expiry_status: str
    cap_share_of_upper_limit: float | None
    production_authority: str
    production_freshness: str
    latest_observed_season: str
    latest_observed_stats: Dict[str, Any]
    career_totals: Dict[str, Any]
    evidenced_role: str
    evidence_dimensions: Tuple[str,...]
    missing_dimensions: Tuple[str,...]
    provenance: Tuple[Dict[str,Any],...]
    limitations: Tuple[str,...]

    @property
    def evidence_complete_for_market_valuation(self) -> bool:
        return not self.missing_dimensions

    def to_dict(self)->Dict[str,Any]:
        p=asdict(self); p["evidence_dimensions"]=list(self.evidence_dimensions);p["missing_dimensions"]=list(self.missing_dimensions);p["provenance"]=[dict(x) for x in self.provenance];p["limitations"]=list(self.limitations);return p

def resolve_player_asset_state(*, player_entity_id:str="", player_name:str="", as_of:str|date|None=None)->PlayerAssetState:
    from Knowledge.Intelligence.Entities.entity_registry import find_by_id, SEED_ENTITIES
    from Knowledge.Intelligence.Public.public_player_profiles import profile_for_entity
    from Knowledge.Intelligence.Public.player_evidence import player_evidence, authoritative_statistical_view
    from Knowledge.Contracts.player_contract_state import resolve_player_contract_state
    target=as_of if isinstance(as_of,date) else date.fromisoformat(str(as_of)) if as_of else date.today()
    entity=find_by_id(player_entity_id) if player_entity_id else next((e for e in SEED_ENTITIES if e.entity_type=="player" and e.canonical_name.casefold()==player_name.casefold()),None)
    if entity is None or entity.entity_type!="player": raise LookupError("No canonical public player identity is available for that player.")
    profile=profile_for_entity(entity)
    evidence=player_evidence(entity.canonical_name,team=entity.team,position=entity.position,birth_date=entity.birth_date)
    stats=authoritative_statistical_view(evidence) if evidence else {"authority":"unavailable","season_series":[],"recent_window":[],"career":{},"freshness":{},"source":""}
    freshness=stats.get("freshness") if isinstance(stats.get("freshness"),dict) else {}
    recent=stats.get("recent_window") if isinstance(stats.get("recent_window"),list) else []
    latest=dict(recent[0]) if recent else {}
    contract=None
    try: contract=resolve_player_contract_state(player_entity_id=entity.entity_id,as_of=target)
    except LookupError: pass
    age=_age(entity.birth_date,target)
    dimensions=["identity","biographical_context","organizational_relationship"]
    missing=[];limitations=[];prov=[{"authority":"public_entity_registry","entity_id":entity.entity_id}]
    if stats.get("authority")=="canonical_statistical_evidence":
        dimensions.append("canonical_statistical_evidence");prov.append({"authority":"canonical_player_statistical_evidence","source":stats.get("source","")})
        if freshness.get("stale_for_current_rating"):
            missing.append("current_production_state");limitations.append("Canonical statistical evidence is stale for a current player-value conclusion.")
    else:
        missing.append("canonical_statistical_evidence");limitations.append("Canonical statistical evidence is unavailable for this player/date.")
    if contract:
        dimensions.append("professional_contract_control");prov.extend(dict(x) for x in contract.provenance)
    else:
        missing.append("professional_contract_control");limitations.append("No canonical professional contract state is registered for this player/date.")
    # These are intentionally not inferred from identity/profile prose.
    missing.extend(["verified_deployment_and_usage","injury_availability_state","market_or_acquisition_cost_evidence"])
    limitations.append("Athena does not assign a market/trade-value score from identity, reputation, or contract evidence alone.")
    role=str(getattr(profile,"role","") or "") if profile else ""
    if role: dimensions.append("seeded_public_role_context")
    return PlayerAssetState(
        player_entity_id=entity.entity_id,player_name=entity.canonical_name,as_of=target.isoformat(),
        team_id=entity.team,team_name="",position=entity.position,age=age,career_stage=_career_stage(age),
        organizational_relationship="current_team_identity" if entity.team else "unknown",
        contract_status="canonical_active_contract" if contract else "contract_evidence_unavailable",
        contract_id=contract.contract_id if contract else "",aav=contract.aav if contract else None,
        effective_to=contract.effective_to if contract else "",expiry_status=contract.expiry_status if contract else "",
        cap_share_of_upper_limit=round(contract.cap_share(target),6) if contract else None,
        production_authority=str(stats.get("authority") or "unavailable"),
        production_freshness=str(freshness.get("status") or "unavailable"),
        latest_observed_season=str(latest.get("season") or freshness.get("latest_season") or ""),
        latest_observed_stats=latest,career_totals=dict(stats.get("career") or {}),
        evidenced_role=role,evidence_dimensions=tuple(dict.fromkeys(dimensions)),
        missing_dimensions=tuple(dict.fromkeys(missing)),provenance=tuple(prov),limitations=tuple(dict.fromkeys(limitations)))
