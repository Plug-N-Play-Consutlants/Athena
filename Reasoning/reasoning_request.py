from dataclasses import dataclass
from typing import Any


@dataclass
class ReasoningRequest:
    reasoning_type: str
    subject: Any
    evidence_bundle: Any = None
    mode: str = "fantasy"
