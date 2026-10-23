"""Select an executable Athena specialist or an explicit legacy fallback."""
from __future__ import annotations

from Athena.execution_registry import SPECIALISTS


def select_executable_route(question: str, mode: str, context=None) -> tuple[str, str]:
    from Athena.intent_planner import plan_capability

    from Athena.diagnostic_intent import is_diagnostic_inquiry
    if is_diagnostic_inquiry(question):
        return "athena_runtime_diagnostics", "athena_diagnostic_intent"

    from Athena.fantasy_team_subject import named_team_roster_subject
    if named_team_roster_subject(question, context):
        return "fantasy_roster_diagnostic", "verified_named_fantasy_team_roster_assignment"

    from Athena.entry_policy import select_entry_route
    entry = select_entry_route(question, mode)
    if entry.route:
        return entry.route, "athena_entry_policy:" + entry.route

    plan = plan_capability(question, mode)
    route = str(getattr(plan, "route", "") or "")
    if (
        any(name in question.casefold() for name in ("jhlpaa", "fantrax"))
        and route == "public_player_comparison"
        and any(term in question.casefold() for term in ("fantasy", "keeper", "roster slot", "scoring"))
    ):
        return "league_player_comparison", "explicit_public_to_fantasy_comparison"
    # A decision inquiry outranks general current-season evidence acquisition.
    # The decision specialist may consume team evidence, but the evidence route
    # must never replace the user's trade/contract objective.
    if mode == 'public' and route == 'public_nhl_decision_inquiry':
        return route, 'athena_decision_objective_precedence'
    # An explicitly named private fantasy league retains its domain in either
    # presentation mode. Public RSS is not a substitute for canonical league data.
    if any(name in question.casefold() for name in ("jhlpaa", "fantrax")) and any(
        term in question.casefold() for term in ("report", "recap", "standings", "scoring", "league", "week", "trade")
    ):
        return "", "explicit_fantasy_league_domain"
    if mode == 'public':
        from Athena.public_team_performance import team_investigation_target
        if team_investigation_target(question) is not None:
            return 'public_current_season_team_investigation', 'canonical_nhl_team_investigation'
    if mode == "public" and route == "ambiguous_public_entity":
        from Athena.public_identity import resolve_public_player
        match = resolve_public_player(question)
        if match is not None and match.entity is not None and match.status == "qualified_resolved":
            from Reasoning.public_player_questions import classify_player_question
            inquiry = classify_player_question(question)
            return ("public_player_identity" if inquiry == "profile" else "public_player_investigation"), "qualified_public_identity"
    if route in SPECIALISTS:
        return route, "athena_intent_plan"
    if mode == "public":
        from Athena.public_identity import resolve_public_player
        # Short named identity requests belong to Athena's public registry.
        # Broader questions retain their analytical and event routes.
        if len(question.split()) <= 7 and not any(token in question.lower() for token in ("?", "why ", "how ", "what ", "latest ", "news ", "compare ", " vs ")):
            if resolve_public_player(question) is not None:
                return "public_player_identity", "qualified_public_identity"
        from Knowledge.Events.live_intelligence import is_recent_event_query
        if is_recent_event_query(question):
            return "live_event_intelligence", "recent_event_detection"
    return "", "legacy_fallback"
