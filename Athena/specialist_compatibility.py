"""Explicit compatibility adapter for inquiries not yet registered in Athena.

Athena owns route selection. Existing Scout handlers remain available only as
the bounded implementation for routes that have not yet been ported.
"""
from __future__ import annotations

from typing import Any, Dict


def execute_existing_specialist(question: str, *, mode: str, context: Any = None) -> Dict[str, Any]:
    from Scout.conversation.router import route_question

    return route_question(question, context, mode=mode)
