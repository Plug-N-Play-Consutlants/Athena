"""Athena-owned routing adapters for established Scout entry capabilities."""
from __future__ import annotations

from typing import Any


def execute_league_recap(ctx: Any, question: str) -> dict[str, Any]:
    from Scout.conversation.router import analyze_league

    return analyze_league(ctx, question)


def execute_period_standings(ctx: Any, question: str) -> dict[str, Any]:
    from Scout.conversation.router import _league_standings_inquiry

    return _league_standings_inquiry(ctx, question)


def execute_fantasy_trade_investigation(ctx: Any, question: str) -> dict[str, Any]:
    from Scout.conversation.router import _fantasy_trade_investigation

    return _fantasy_trade_investigation(ctx, question)
