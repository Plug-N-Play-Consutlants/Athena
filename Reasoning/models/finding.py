from dataclasses import dataclass, field
from .evidence_reference import EvidenceReference
from .confidence import Confidence

@dataclass(slots=True)
class Finding:
    category:str
    statement:str
    importance:float=1.0
    confidence:Confidence|None=None
    supporting_evidence:list[EvidenceReference]=field(default_factory=list)
    contradicting_evidence:list[EvidenceReference]=field(default_factory=list)
    rule_references:list[EvidenceReference]=field(default_factory=list)
