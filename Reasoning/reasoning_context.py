from dataclasses import dataclass
@dataclass
class ReasoningContext:
    sport:str="NHL"
    league:str|None=None
    organization:str|None=None
    consumer:str="Scout"
