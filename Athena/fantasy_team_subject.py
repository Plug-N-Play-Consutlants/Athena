"""Resolve explicitly named fantasy teams and the assignment without fuzzy guesses.

Provider/league evidence owns team names. Public UI mode does not erase an
explicit, exact fantasy-team subject. Never treat fragments as team identity.
"""
from __future__ import annotations

import re
from typing import Any


def _names(context: Any) -> list[str]:
    found: set[str] = set()
    if context is None:
        return []
    for row in getattr(context, 'team_profiles', None) or []:
        if isinstance(row, dict) and row.get('team_name'):
            found.add(str(row['team_name']).strip())
    for row in getattr(context, 'player_master', None) or []:
        if isinstance(row, dict) and row.get('owner_team'):
            found.add(str(row['owner_team']).strip())
    return sorted((name for name in found if len(name) >= 4), key=lambda name: (-len(name), name))


def named_team_roster_subject(question: str, context: Any) -> str | None:
    """Only a unique whole-name team mention *with roster-evaluation intent*."""
    q = str(question or '').strip()
    if not re.search(r'\b(roster|lineup|team|forwards?|defen[cs]e|goaltend\w*|positional)\b', q, re.I):
        return None
    if not re.search(r'\b(improv\w*|weakness\w*|strength\w*|upgrade\w*|assess|evaluat\w*|diagnos\w*|need\w*|tradeoffs?|alternatives?|recommend\w*|holes?)\b', q, re.I):
        return None
    matches = [name for name in _names(context) if re.search(r'(?<!\w)' + re.escape(name) + r'(?!\w)', q, re.I)]
    # Nested names are possible; don't mistake a substring of another verified
    # team for a second team. Multiple distinct clubs require another route.
    if len(matches) != 1:
        return None
    return matches[0]
