from dataclasses import dataclass, field

@dataclass(slots=True)
class Confidence:
    score:float
    level:str
    explanation:str=""
    penalties:list[str]=field(default_factory=list)
