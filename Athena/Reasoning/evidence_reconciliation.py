"""Evidence reconciliation primitives for analytical investigations.

A failed verification attempt narrows what Athena may assert; it does not erase
independently supported components of the user's hypothesis.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Iterable, Dict, Any

VALID_STATES={"established","corroborated","evidence_supported_inference","unresolved","contradicted","superseded","user_supplied_hypothesis"}

@dataclass(frozen=True)
class ReconciledClaim:
    claim:str
    state:str
    support:tuple[str,...]=()
    conflicts:tuple[str,...]=()
    note:str=""
    def to_dict(self)->Dict[str,Any]: return asdict(self)

def reconcile_claim(claim:str, *, verified:bool=False, contradicted:bool=False,
                    independent_support:Iterable[str]=(), conflicts:Iterable[str]=(),
                    superseded:bool=False)->ReconciledClaim:
    support=tuple(str(x) for x in independent_support if str(x).strip())
    conflict_rows=tuple(str(x) for x in conflicts if str(x).strip())
    if superseded: state="superseded"
    elif contradicted: state="contradicted"
    elif verified and support: state="corroborated"
    elif verified: state="established"
    else: state="unresolved"
    note=""
    if state=="unresolved" and support:
        note="The specific claim remains unverified, but independently supported components remain analytically usable and must not be discarded."
    return ReconciledClaim(str(claim),state,support,conflict_rows,note)

def surviving_hypothesis(claim:ReconciledClaim)->Dict[str,Any]:
    return {"specific_claim_state":claim.state,"independent_support":list(claim.support),
            "may_support_broader_inference":bool(claim.support) and claim.state not in {"contradicted","superseded"},
            "must_not_assert_specific_claim":claim.state not in {"established","corroborated"}}
