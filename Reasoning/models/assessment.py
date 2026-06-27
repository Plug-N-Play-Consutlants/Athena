from dataclasses import dataclass, field
from .finding import Finding
from .confidence import Confidence

@dataclass(slots=True)
class Assessment:
    overall_summary:str=""
    strengths:list[str]=field(default_factory=list)
    weaknesses:list[str]=field(default_factory=list)
    opportunities:list[str]=field(default_factory=list)
    risks:list[str]=field(default_factory=list)
    key_findings:list[Finding]=field(default_factory=list)
    overall_confidence:Confidence|None=None
