from dataclasses import dataclass
from .reasoning_request import ReasoningRequest
from .reasoning_context import ReasoningContext

@dataclass
class ReasoningSession:
    session_id:str
    request:ReasoningRequest
    context:ReasoningContext
    evidence_bundle:object|None=None
    reasoning_object:object|None=None
