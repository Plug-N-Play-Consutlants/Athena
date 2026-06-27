"""Event engine facade namespace.

This package exposes deterministic event algorithms from a stable Engine import
surface while preserving Knowledge.Events as the source of event facts and
registries.
"""
from __future__ import annotations

from Engine.Events.facade import EventEngineFacade, build_event_engine
from Engine.EventReasoning import EventReasoningEngine, EventReasoningResult, EventReasoningBatch

__all__ = ["EventEngineFacade", "build_event_engine", "EventReasoningEngine", "EventReasoningResult", "EventReasoningBatch"]
