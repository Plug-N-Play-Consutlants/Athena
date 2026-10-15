"""Select an executable Athena specialist or an explicit legacy fallback."""
from __future__ import annotations

from Athena.execution_registry import SPECIALISTS


def select_executable_route(question: str, mode: str) -> tuple[str, str]:
    from Athena.intent_planner import plan_capability

    from Athena.entry_policy import select_entry_route
    entry = select_entry_route(question, mode)
    if entry.route:
        # Athena decides the objective; Scout remains the explicit presentation
        # adapter until the legacy reporting contracts are ported.
        return "", "athena_entry_policy:" + entry.route

    # An explicitly named private fantasy league retains its domain in either
    # presentation mode. Public RSS is not a substitute for canonical league data.
    if any(name in question.casefold() for name in ("jhlpaa", "fantrax")) and any(
        term in question.casefold() for term in ("report", "recap", "standings", "scoring", "league", "week", "trade")
    ):
        return "", "explicit_fantasy_league_domain"
    plan = plan_capability(question, mode)
    route = str(getattr(plan, "route", "") or "")
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
