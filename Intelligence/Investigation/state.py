"""Bounded working investigation state. Session-scoped, not durable personal memory."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List
from uuid import uuid4

INVESTIGATION_STATE_VERSION = "0.6.4.1.0"

@dataclass
class InvestigationState:
    topic: str
    strategy_id: str
    investigation_id: str = field(default_factory=lambda: f"inv_{uuid4().hex[:12]}")
    status: str = "active"
    entities: List[str] = field(default_factory=list)
    findings: List[str] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)
    turns: int = 0
    def record_turn(self): self.turns += 1
    def add_entity(self, value):
        value=str(value or '').strip()
        if value and value not in self.entities: self.entities.append(value)
    def add_finding(self, value):
        value=str(value or '').strip()
        if value and value not in self.findings: self.findings.append(value)
    def add_open_question(self, value):
        value=str(value or '').strip()
        if value and value not in self.open_questions: self.open_questions.append(value)
    def to_dict(self):
        d=asdict(self); d['version']=INVESTIGATION_STATE_VERSION; return d

class InvestigationSessionRegistry:
    def __init__(self):
        self._states: Dict[str, InvestigationState] = {}
        self._active_by_session: Dict[str, str] = {}
    def start(self, topic, strategy_id, *, session_id="default", entities=()):
        state=InvestigationState(topic=topic, strategy_id=strategy_id)
        for entity in entities: state.add_entity(entity)
        self._states[state.investigation_id]=state
        self._active_by_session[str(session_id or 'default')]=state.investigation_id
        return state
    def get(self, investigation_id): return self._states.get(str(investigation_id or ''))
    def active(self, session_id="default"):
        iid=self._active_by_session.get(str(session_id or 'default'))
        return self.get(iid) if iid else None
    def continue_or_start(self, topic, strategy_id, *, session_id="default", entities=()):
        current=self.active(session_id)
        incoming={str(e).strip().lower() for e in entities if str(e).strip()}
        current_entities={e.lower() for e in current.entities} if current else set()
        compatible = bool(current and current.status == 'active' and (not incoming or incoming.intersection(current_entities)))
        if compatible:
            current.strategy_id = strategy_id
            for entity in entities: current.add_entity(entity)
            return current, True
        return self.start(topic, strategy_id, session_id=session_id, entities=entities), False
    def close(self, investigation_id):
        state=self.get(investigation_id)
        if state: state.status='closed'
        return state
