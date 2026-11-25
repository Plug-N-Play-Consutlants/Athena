"""Athena-owned precedence policy for established legacy league objectives.

This classifies *execution ownership*, not evidence or final answers. Existing
Scout adapters remain until the response contract is migrated safely.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from Athena.audit_intent import affirmative_audit_request

@dataclass(frozen=True)
class EntryDecision:
    route: str
    reason: str


def select_entry_route(question: str, mode: str = 'fantasy') -> EntryDecision:
    q = (question or '').casefold()
    mode = (mode or 'fantasy').strip().lower()
    explicit = any(term in q for term in ('jhlpaa', 'fantrax'))
    fantasy = (mode != 'public' or explicit) and any(term in q for term in ('jhlpaa', 'fantrax', 'my league', 'around the league'))
    editorial = bool(re.search(r'\b(report|recap|summary|summari[sz]e|analy[sz]e|analize|review|biggest stories|developments)\b', q)) and bool(re.search(r'\b(league|jhlpaa|fantrax|standings|scoring)\b', q))
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
                     and affirmative_audit_request(question)
                     and bool(re.search(r'\b(?:weeks?|periods?)\s*\d+', q))
                     and bool(re.search(r'\b(scoring|points|scores?|rosters?|active|standings)\b', q)))
    # A comparison across multiple weeks with transactions/storylines is a
    # composite investigation, not a standings-only query. Preserve user scope.
    from Athena.Investigation.transaction_event_intelligence import resolve_reporting_periods
    try:
        requested_weeks = resolve_reporting_periods(question)
    except ValueError:
        requested_weeks = []
    composite_comparison = (explicit and len(requested_weeks) > 1
                            and bool(re.search(r"\b(compare|comparison|changes?|trends?|developing|across)\b", q))
                            and (sections >= 2 or 'transactions' in q or 'storylines' in q))
    if scoring_audit:
        return EntryDecision('league_recap', 'explicit_period_scoring_reconciliation')
    rolling_comparison = (explicit and bool(re.search(r'\b(?:last|latest|most recent)\s+(?:three|3)\s+(?:completed\s+)?(?:scoring\s+)?(?:weeks?|periods?)\b', q))
                          and (sections >= 2 or editorial or 'races' in q or 'storylines' in q))
    if rolling_comparison:
        return EntryDecision('league_multi_period_analysis', 'last_three_completed_periods')
    if composite_comparison:
        return EntryDecision('league_multi_period_analysis', 'explicit_multi_period_composite_inquiry')
    if explicit and re.search(r'\b(?:write|draft|prepare|produce)\b', q) and re.search(r'\b(?:editorial|league\s+report|league\s+recap)\b', q):
        return EntryDecision('league_recap', 'explicit_written_editorial_request')
    if fantasy and (broad_report or (editorial and sections >= 2)):
        return EntryDecision('league_recap', 'composite_weekly_editorial_request')
    # Explicit league questions retain their fantasy evidence domain even when
    # the presentation mode is Public. Route by inquiry objective, not UI mode.
    if explicit and re.search(r'\b(top\s*\d+|leaders?|leading|most|highest|best)\b', q) and re.search(r'\b(players?|producers?|production|points|goals|assists|g\s*\+\s*a)\b', q):
        return EntryDecision('league_player_period_leaders', 'explicit_league_player_production')
    # A named team's performance is an investigation, not a calendar question.
    # Inspect explicit team framing before a narrow scoring-period question.
    # A league-wide editorial is already handled above.
    team_performance = (explicit and
        bool(re.search(r'\b(?:analy[sz]e|assess|evaluate|explain|review|break\s*down|how\s+did)\b', q)) and
        bool(re.search(r'\b(?:performance|performed|results|scoring|points|contributed|underperformed)\b', q)) and
        bool(re.search(r'\b(?:team|roster|rostered|[a-z][a-z .’\'-]+[’\']s\s+(?:performance|results))\b', q)) and
        bool(re.search(r'\b(?:period|week)\s*\d+\b', q)))
    if team_performance:
        return EntryDecision('league_team_period_performance', 'explicit_named_team_period_performance')
    # Period boundaries must be an explicit calendar/finalization objective;
    # merely saying 'which players ... in scoring period 8' is not one.
    boundary_objective = bool(re.search(
        r'\b(?:when\s+(?:did|does|was|is)|what\s+(?:date|dates|day)|exact\s+dates|'
        r'period\s+(?:start|end|boundary|calendar)|'
        r'which\s+(?:was|is)\s+(?:the\s+)?(?:last|latest|most\s+recently)\s+completed)\b', q))
    if explicit and boundary_objective and re.search(r'\b(?:scoring\s+period|completed\s+period|last\s+completed|most\s+recently\s+completed)\b', q):
        return EntryDecision('league_scoring_period_boundary', 'explicit_league_calendar_question')
    standings = explicit and 'standings' in q and any(t in q for t in ('week', 'period', 'season', 'historical', 'movement'))
    if standings and not editorial:
        return EntryDecision('league_period_standings', 'explicit_period_standings')
    temporal_recap = bool(re.search(r'\b(this|past|last|current)\s+(week|period)\b|\bweek\s*\d+\b', q)) and bool(re.search(r'\b(what happened|what changed|happening|happened|developments|activity|recap|roundup)\b', q))
    recap = fantasy and (temporal_recap or any(t in q for t in ('week 2', 'week two', 'weekly report', 'league period', 'around the jhlpaa', 'last week', 'weekly recap')))
    trade = fantasy and 'trade' in q and any(t in q for t in ('analy', 'assess', 'reconstruct', 'explain', 'implications'))
    # An explicitly named fantasy league stays in its evidence domain even in Public mode.
    # 'summary of the previous week in the JHLPAA' must not need a magic command.
    named_period_summary = explicit and bool(re.search(r'\b(summary|summari[sz]e|recap|report|roundup|overview)\b', q)) and bool(re.search(r'\b(previous|prior|past|last|this|current)\s+(?:week|period)\b|\bweek\s*\d+\b', q))
    if recap or named_period_summary or (editorial and (mode != 'public' or explicit)):
        return EntryDecision('league_recap', 'explicit_editorial_objective')
    if trade:
        return EntryDecision('fantasy_trade_investigation', 'explicit_trade_objective')
    return EntryDecision('', 'registered_specialist_or_compatibility')
