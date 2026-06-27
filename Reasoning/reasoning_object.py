from dataclasses import dataclass, field
@dataclass
class ReasoningObject:
    summary:str=""
    findings:list=field(default_factory=list)
    confidence:float=0.0
    rule_citations:list=field(default_factory=list)
