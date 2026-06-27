from dataclasses import dataclass, field
from typing import Any

@dataclass(slots=True)
class EvidenceReference:
    source:str
    source_type:str
    title:str
    summary:str=""
    confidence:float=1.0
    weight:float=1.0
    uri:str|None=None
    graph_node:str|None=None
    metadata:dict[str,Any]=field(default_factory=dict)
