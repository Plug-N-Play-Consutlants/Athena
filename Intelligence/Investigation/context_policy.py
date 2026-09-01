"""Context priority contract used between investigation and composition."""
from __future__ import annotations
from dataclasses import dataclass
from enum import IntEnum
from typing import Dict

class ContextPriority(IntEnum):
    EXCLUDED = 0
    OPTIONAL = 1
    USEFUL = 2
    ESSENTIAL = 3

@dataclass(frozen=True)
class ContextPolicy:
    strategy_id: str
    priorities: Dict[str, ContextPriority]

    def priority_for(self, context_key: str) -> ContextPriority:
        return self.priorities.get(str(context_key or "").strip().lower(), ContextPriority.OPTIONAL)

    @classmethod
    def for_strategy(cls, strategy_id: str) -> "ContextPolicy":
        sid = str(strategy_id or "balanced")
        if sid in {"brief_update", "news_update"}:
            return cls(sid, {"current_event": ContextPriority.ESSENTIAL, "identity": ContextPriority.USEFUL, "historical_context": ContextPriority.OPTIONAL, "organizational_context": ContextPriority.OPTIONAL})
        if sid == "comparison":
            return cls(sid, {"identity": ContextPriority.ESSENTIAL, "comparison_framework": ContextPriority.ESSENTIAL, "historical_context": ContextPriority.USEFUL, "contradictory_evidence": ContextPriority.USEFUL})
        if sid in {"entity_profile", "deep_analysis", "advisory"}:
            return cls(sid, {"identity": ContextPriority.ESSENTIAL, "historical_context": ContextPriority.USEFUL, "organizational_context": ContextPriority.USEFUL, "contradictory_evidence": ContextPriority.USEFUL, "limitations": ContextPriority.ESSENTIAL})
        return cls(sid, {"identity": ContextPriority.USEFUL, "limitations": ContextPriority.USEFUL})
