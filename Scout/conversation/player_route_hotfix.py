"""Scout player-route helper.

Routes obvious player-analysis prompts through Player Intelligence while
explicitly excluding league/team/workspace prompts. This prevents broad fantasy
questions such as "Analyze my league" from being treated as player names.
"""
from __future__ import annotations

import re

_PLAYER_ANALYSIS_PATTERNS = (
    r"\banaly[sz]e\s+",
    r"\bassess\s+",
    r"\bevaluate\s+",
    r"\bprofile\s+",
    r"\btell\s+me\s+about\s+",
    r"\bshow\s+me\s+",
    r"\bwho\s+is\s+",
    r"\bwhat\s+do\s+you\s+think\s+of\s+",
)

_LEAGUE_TERMS = (
    "league",
    "my league",
    "fantasy league",
    "team weaknesses",
    "roster weaknesses",
    "draft prep",
    "draft preparation",
    "my team",
    "my roster",
    "waiver wire",
    "free agents",
    "league market",
    "manager activity",
    "active managers",
    "standings",
    "keepers",
    "contracts",
)


def looks_like_league_or_team_intent(question: str) -> bool:
    q = (question or "").strip().lower()
    if not q:
        return False
    return any(term in q for term in _LEAGUE_TERMS)


def looks_like_player_analysis(question: str) -> bool:
    q = (question or "").strip().lower()
    if not q:
        return False
    if looks_like_league_or_team_intent(q):
        return False
    return any(re.search(pattern, q) for pattern in _PLAYER_ANALYSIS_PATTERNS)
