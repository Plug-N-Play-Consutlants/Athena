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
    # A multi-section weekly editorial request is one investigation, even when
    # its requested sections include top player producers or a scoring calendar.
    # Route the whole request before selecting narrower specialist questions.
    broad_report = bool(re.search(r'\b(weekly\s+(?:league\s+)?report|weekly\s+recap|league\s+(?:report|recap|roundup)|full\s+(?:weekly\s+)?report|complete\s+(?:weekly\s+)?report|around\s+the\s+(?:jhlpaa|league))\b', q))
    sections = sum(bool(re.search(pattern, q)) for pattern in (
        r'\bstandings|rankings|movement\b',
        r'\bplayers?|performances?|producers?|g\s*\+\s*a\b',
        r'\btransactions?|waivers?|free\s+agents?|adds?|drops?\b',
        r'\btrades?|trading\s+blocks?\b',
        r'\b(editorial|stories|analysis|highlights|movers|shakers)\b',
    ))
    # A request to reconcile specific league scoring periods needs the complete
    # Athena period-audit path even when the user does not ask for an editorial.
    # Otherwise it can be misrouted as a standings-only or generic inquiry.
    scoring_audit = (explicit
                     and bool(re.search(r'\b(reconcile|reconciliation|audit|verify)\b', q))
                     and bool(re.search(r'\b(?:weeks?|periods?)\s*\d+', q))
                     and bool(re.search(r'\b(scoring|points|scores?|rosters?|active|standings)\b', q)))
    if scoring_audit:
        return EntryDecision('league_recap', 'explicit_period_scoring_reconciliation')
    if fantasy and (broad_report or (editorial and sections >= 2)):
        return EntryDecision('league_recap', 'composite_weekly_editorial_request')
    # Explicit league questions retain their fantasy evidence domain even when
    # the presentation mode is Public. Route by inquiry objective, not UI mode.
    if explicit and re.search(r'\b(top\s*\d+|leaders?|leading|most|highest|best)\b', q) and re.search(r'\b(players?|producers?|production|points|goals|assists|g\s*\+\s*a)\b', q):
        return EntryDecision('league_player_period_leaders', 'explicit_league_player_production')
    if explicit and re.search(r'\b(scoring period|completed period|last completed|most recently completed)\b', q) and re.search(r'\b(when|which|what|date|ended|completed|latest|recent)\b', q):
        return EntryDecision('league_scoring_period_boundary', 'explicit_league_calendar_question')
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
