"""Athena-owned precedence policy for established legacy league objectives.

This classifies *execution ownership*, not evidence or final answers. Existing
Scout adapters remain until the response contract is migrated safely.
"""
from __future__ import annotations
import re
from dataclasses import dataclass

@dataclass(frozen=True)
class EntryDecision:
    route: str
    reason: str


def select_entry_route(question: str, mode: str = 'fantasy') -> EntryDecision:
    q = (question or '').casefold()
    mode = (mode or 'fantasy').strip().lower()
    explicit = any(term in q for term in ('jhlpaa', 'fantrax'))
    fantasy = (mode != 'public' or explicit) and any(term in q for term in ('jhlpaa', 'fantrax', 'my league', 'around the league'))
    editorial = bool(re.search(r'\b(report|recap|summari[sz]e|analy[sz]e|analize|review|biggest stories|developments)\b', q)) and bool(re.search(r'\b(league|jhlpaa|fantrax|standings|scoring)\b', q))
    standings = explicit and 'standings' in q and any(t in q for t in ('week', 'period', 'season', 'historical', 'movement'))
    if standings and not editorial:
        return EntryDecision('league_period_standings', 'explicit_period_standings')
    temporal_recap = bool(re.search(r'\b(this|past|last|current)\s+(week|period)\b|\bweek\s*\d+\b', q)) and bool(re.search(r'\b(what happened|what changed|happening|happened|developments|activity|recap|roundup)\b', q))
    recap = fantasy and (temporal_recap or any(t in q for t in ('week 2', 'week two', 'weekly report', 'league period', 'around the jhlpaa', 'last week', 'weekly recap')))
    trade = fantasy and 'trade' in q and any(t in q for t in ('analy', 'assess', 'reconstruct', 'explain', 'implications'))
    if recap or (editorial and (mode != 'public' or explicit)):
        return EntryDecision('league_recap', 'explicit_editorial_objective')
    if trade:
        return EntryDecision('fantasy_trade_investigation', 'explicit_trade_objective')
    return EntryDecision('', 'registered_specialist_or_compatibility')
