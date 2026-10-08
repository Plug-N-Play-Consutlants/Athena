"""NHL transaction/scenario engine over canonical state.

Scenarios are immutable analytical overlays. They never mutate Knowledge state.
Contract deltas require canonical professional contract evidence; unsupported
mechanics remain explicit unresolved inputs rather than inferred facts.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, Tuple

from Reasoning.Cap.cap_reasoning import ADJUSTMENT_CLASSES, evaluate_team_cap_state

@dataclass(frozen=True)
class ScenarioOperation:
    operation: str  # acquire_contract | release_contract
    player_entity_id: str
    player_name: str
    contract_id: str
    full_aav: int
    cap_charge_delta: int
    retained_cap_amount: int = 0
    evidence_status: str = "canonical"

    def to_dict(self) -> Dict[str, Any]: return asdict(self)

@dataclass(frozen=True)
class TransactionScenario:
    scenario_id: str
    team_id: str
    team_name: str
    league_year: str
    as_of: str
    status: str
    baseline_cap_charge_total: int | None
    net_cap_charge_delta: int | None
    hypothetical_cap_charge_total: int | None
    operations: Tuple[ScenarioOperation, ...]
    assumptions: Tuple[str, ...]
    unresolved_inputs: Tuple[str, ...]
    cap_determination: Dict[str, Any]
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        d=asdict(self); d["operations"]=[x.to_dict() for x in self.operations]; return d

def _operation(contract: Any, operation: str, *, retained_cap_amount: int = 0) -> ScenarioOperation:
    if operation not in {"acquire_contract","release_contract"}: raise ValueError(f"Unsupported scenario operation: {operation}")
    retained=max(0,int(retained_cap_amount or 0))
    if retained > int(contract.aav): raise ValueError("Retained cap amount cannot exceed canonical contract AAV.")
    # For an acquiring club, retained salary reduces incoming charge. For a
    # releasing club, retained salary remains as a charge and therefore reduces
    # the amount removed from its books.
    effective=max(0,int(contract.aav)-retained)
    delta=effective if operation=="acquire_contract" else -effective
    return ScenarioOperation(operation,contract.player_entity_id,contract.player_name,contract.contract_id,int(contract.aav),delta,retained)

def evaluate_transaction_scenario(team_state: Any, league_context: Any, *, scenario_id: str,
                                  operations: Iterable[ScenarioOperation],
                                  verified_baseline_cap_charge_total: int | None = None,
                                  resolved_adjustment_classes: Tuple[str,...] = (),
                                  assumptions: Tuple[str,...] = ()) -> TransactionScenario:
    ops=tuple(operations); unresolved=[]
    if not ops: unresolved.append("transaction_operations")
    if any(o.evidence_status != "canonical" for o in ops): unresolved.append("canonical_transaction_contract_evidence")
    delta=sum(o.cap_charge_delta for o in ops) if ops and not unresolved else None
    hypothetical=None if verified_baseline_cap_charge_total is None or delta is None else int(verified_baseline_cap_charge_total)+delta
    # The canonical team's completeness gate still applies. For controlled/future
    # complete ledgers, an injected verified baseline permits numeric execution.
    class ScenarioTeam:
        team_id=team_state.team_id; team_name=team_state.team_name; as_of=team_state.as_of
        aggregate_permitted = bool(getattr(team_state,"aggregate_permitted",False)) or verified_baseline_cap_charge_total is not None
    cap=evaluate_team_cap_state(ScenarioTeam(),league_context,verified_cap_charge_total=hypothetical,
                                resolved_adjustment_classes=resolved_adjustment_classes)
    unresolved.extend(cap.unresolved_inputs)
    unresolved=tuple(dict.fromkeys(unresolved))
    status="scenario_indeterminate" if unresolved or hypothetical is None else "scenario_evaluated"
    if delta is None:
        explanation="The hypothetical is represented, but its cap-charge delta cannot be calculated from canonical contract evidence."
    else:
        direction="adds" if delta>=0 else "removes"
        explanation=(f"This hypothetical {direction} ${abs(delta)/1_000_000:.2f}M in evidenced contract cap charge for {team_state.team_name}. "
                     + (f"Against the verified baseline, hypothetical cap charges are ${hypothetical/1_000_000:.2f}M. " if hypothetical is not None else "Athena does not have a verified complete baseline team ledger, so final cap usage/headroom remains indeterminate. ")
                     + "The scenario is an analytical overlay and does not alter canonical current state.")
    return TransactionScenario(scenario_id,team_state.team_id,team_state.team_name,league_context.league_year,team_state.as_of,status,
                               verified_baseline_cap_charge_total,delta,hypothetical,ops,tuple(assumptions),unresolved,cap.to_dict(),explanation)

def acquire_contract(contract: Any, *, retained_cap_amount: int = 0) -> ScenarioOperation:
    return _operation(contract,"acquire_contract",retained_cap_amount=retained_cap_amount)

def release_contract(contract: Any, *, retained_cap_amount: int = 0) -> ScenarioOperation:
    return _operation(contract,"release_contract",retained_cap_amount=retained_cap_amount)
