"""Canonical evidence-bounded player intelligence models."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List

EVIDENCE_STATES={"established","supported_inference","bounded_inference","unresolved","not_applicable"}

@dataclass
class PlayerIntelligence:
    player: str
    evidence_profile: Dict[str,Any]=field(default_factory=dict)
    development_pathway: Dict[str,Any]=field(default_factory=dict)
    comparative_baselines: List[Dict[str,Any]]=field(default_factory=list)
    opportunity_context: Dict[str,Any]=field(default_factory=dict)
    development_trajectory: Dict[str,Any]=field(default_factory=dict)
    current_impact: Dict[str,Any]=field(default_factory=dict)
    projection: Dict[str,Any]=field(default_factory=dict)
    uncertainty: List[str]=field(default_factory=list)
    def to_dict(self)->Dict[str,Any]: return asdict(self)
