"""Deterministic rules for routing event impact across Athena domains."""
from __future__ import annotations

from typing import Dict, List


def default_impact_rules() -> Dict[str, List[str]]:
    return {
        "injury": ["player", "team", "fantasy", "historical"],
        "return": ["player", "team", "fantasy"],
        "trade": ["player", "team", "organization", "fantasy", "historical"],
        "free_agent_signing": ["player", "team", "organization", "fantasy"],
        "signing": ["player", "team", "organization", "fantasy"],
        "extension": ["player", "team", "organization", "historical"],
        "waiver": ["player", "team", "fantasy"],
        "claim": ["player", "team", "fantasy"],
        "call_up": ["player", "team", "prospect", "fantasy"],
        "send_down": ["player", "team", "prospect", "fantasy"],
        "demotion": ["player", "team", "prospect", "fantasy"],
        "suspension": ["player", "team", "fantasy", "historical"],
        "schedule_change": ["team", "fantasy"],
        "game_result": ["team", "player", "historical"],
        "coaching_change": ["team", "organization", "player"],
        "retirement": ["player", "historical", "organization"],
    }


def domains_for_event_type(event_type: str) -> List[str]:
    return default_impact_rules().get(event_type, ["player", "team"])
