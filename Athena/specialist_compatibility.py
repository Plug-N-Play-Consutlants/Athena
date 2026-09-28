"""Temporary port for existing specialists during Athena pathway migration.

This is deliberately explicit: Scout's router still owns specialist selection
in this build. The adapter is retired as Athena-owned executors are registered.
"""
from __future__ import annotations

from typing import Any, Dict


def execute_existing_specialist(question: str, *, mode: str, context: Any = None) -> Dict[str, Any]:
    from Scout.conversation.router import route_question

    return route_question(question, context, mode=mode)
