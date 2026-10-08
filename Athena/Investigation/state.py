"""First-class bounded investigation state.

InquiryState says what the user asked. InvestigationState records what Athena
actually checked before synthesis so an evidence gap cannot masquerade as an
investigation.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

VALID_STATUSES={"required","satisfied_from_canonical","acquisition_required","refreshed_from_provider","acquired_from_provider","partial","waived","unresolved_after_investigation","no_registered_provider","requires_analytical_inference"}

@dataclass
class RequirementState:
    name:str
    status:str="required"
    providers:List[str]=field(default_factory=list)
    capabilities:List[str]=field(default_factory=list)
    evidence:List[str]=field(default_factory=list)
    note:str=""
    def set(self,status:str,*,provider:str="",capability:str="",evidence:str="",note:str="") -> None:
        if status not in VALID_STATUSES: raise ValueError(status)
        self.status=status
        if provider and provider not in self.providers:self.providers.append(provider)
        if capability and capability not in self.capabilities:self.capabilities.append(capability)
        if evidence and evidence not in self.evidence:self.evidence.append(evidence)
        if note:self.note=note

@dataclass
class InvestigationState:
    inquiry:Dict[str,Any]
    requirements:Dict[str,RequirementState]=field(default_factory=dict)
    capabilities_considered:List[str]=field(default_factory=list)
    capabilities_executed:List[str]=field(default_factory=list)
    evidence:Dict[str,Any]=field(default_factory=dict)
    findings:List[str]=field(default_factory=list)
    uncertainties:List[str]=field(default_factory=list)
    passes:int=0
    saturated:bool=False
    def require(self,*names:str)->None:
        for name in names:
            if name and name not in self.requirements:self.requirements[name]=RequirementState(name)
    def consider(self,name:str)->None:
        if name not in self.capabilities_considered:self.capabilities_considered.append(name)
    def executed(self,name:str)->None:
        self.consider(name)
        if name not in self.capabilities_executed:self.capabilities_executed.append(name)
    def mark(self,name:str,status:str,**kwargs:Any)->None:
        self.require(name);self.requirements[name].set(status,**kwargs)
    def unresolved(self)->List[str]:
        terminal={"unresolved_after_investigation","no_registered_provider","partial","requires_analytical_inference"}
        return [k for k,v in self.requirements.items() if v.status in terminal]
    def to_dict(self)->Dict[str,Any]:
        return {"inquiry":dict(self.inquiry),"requirements":{k:asdict(v) for k,v in self.requirements.items()},"capabilities_considered":list(self.capabilities_considered),"capabilities_executed":list(self.capabilities_executed),"evidence":self.evidence,"findings":list(self.findings),"uncertainties":list(self.uncertainties),"passes":self.passes,"saturated":self.saturated}
