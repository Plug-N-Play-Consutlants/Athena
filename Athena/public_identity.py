"""Bounded public player identity executor."""
from __future__ import annotations

from typing import Any, Dict


def resolve_public_player(question: str) -> Any:
    from Knowledge.Intelligence.Entities.entity_extractor import resolve_qualified_player
    return resolve_qualified_player(question)


def execute_public_player(context: Any, question: str) -> Dict[str, Any]:
    from Knowledge.Intelligence.Public.public_answers import player_profile_answer
    from Knowledge.Intelligence.Public.public_player_profiles import profile_for_entity
    from Scout.conversation.responses import response, developer_info

    match = resolve_public_player(question)
    profile = profile_for_entity(match.entity) if match is not None and match.entity is not None else None
    if profile is not None:
        answer = player_profile_answer(context, profile, question)
        answer.setdefault("developer", {})["identity_resolution"] = match.to_dict()
        return answer
    return response(
        intent="public_player_identity_gap", title="Public player identity needs clarification",
        engine_conclusion="The named public player could not be established with the supplied qualifiers.",
        natural_language_response="I could not match that player and description to one verified public identity. Please clarify the player rather than relying on an unrelated profile.",
        observed_facts=[], known_limitations=["Public player identity is unresolved; fantasy player data cannot establish the intended public identity."],
        confidence=0.3, developer=developer_info("public_player_identity_gap", context.files_loaded, missing=["qualified_public_player_identity"]),
    )


def execute_public_player_investigation(context: Any, question: str) -> Dict[str, Any]:
    from Knowledge.Intelligence.Public.public_player_profiles import profile_for_entity
    from Reasoning.public_player_questions import assess_player_question
    from Scout.conversation.responses import response, developer_info

    match = resolve_public_player(question)
    profile = profile_for_entity(match.entity) if match is not None and match.entity is not None else None
    if profile is None:
        return execute_public_player(context, question)
    assessment = assess_player_question(profile, question)
    bundle = getattr(context, "request_evidence", {}) if context is not None else {}
    player_bundle = bundle.get("player", {}) if isinstance(bundle, dict) else {}
    official = player_bundle.get("official_player_record") if isinstance(player_bundle, dict) else None
    dated_news = player_bundle.get("dated_news", []) if isinstance(player_bundle, dict) else []
    facts = list(assessment["facts"])
    limitations = list(assessment["limitations"])
    conclusion = assessment["conclusion"]
    if isinstance(official, dict) and official:
        statistical = official.get("statistical_evidence", {}) if isinstance(official.get("statistical_evidence"), dict) else {}
        history = [row for row in statistical.get("season_series", official.get("season_history", [])) if isinstance(row, dict)]
        for row in history[:3]:
            facts.append(f"Official NHL season record: {row.get('season')} — {row.get('points')} points in {row.get('gp')} games.")
        if history:
            limitations = [item for item in limitations if "performance" not in item.casefold()]
        target = str(statistical.get("target_season") or official.get("target_season") or "")
        current_rows = [row for row in history if str(row.get("season") or "").replace("-", "").startswith(target[:4])]
        if target and not current_rows and assessment["kind"] == "current_evidence":
            limitations.append(f"Official player record contains no verified games for the target {target[:4]} season.")
    # Reuse the official club-season production pathway when a player landing
    # record is absent or does not cover the target season. This is a bounded
    # same-team, exact-name match, never a fuzzy fantasy identity substitute.
    if assessment["kind"] == "current_evidence":
        from Knowledge.Intelligence.Public.player_evidence import authoritative_statistical_view as _view
        _prior_view = _view(official) if isinstance(official, dict) and official else {}
        _target = str(_prior_view.get("target_season") or "")
        _series = _prior_view.get("season_series") or []
        _has_current = any(str(r.get("season") or "").replace("-", "").startswith(_target[:4]) and isinstance(r.get("gp"), (int, float)) and r["gp"] > 0 for r in _series if isinstance(r, dict)) if _target else False
        if not _has_current:
            try:
                from Athena.public_team_performance import official_team_player_row
                club_row = official_team_player_row(profile.display_name, profile.team)
                if club_row:
                    target = club_row["season"]
                    gp, pts = club_row["gp"], club_row["points"]
                    conclusion = f"{profile.display_name} has verified {target} NHL club-season production: {gp:g} games, {pts:g} points"
                    for key, label in (("goals", "goals"), ("assists", "assists")):
                        if isinstance(club_row.get(key), (int, float)):
                            conclusion += f", {club_row[key]:g} {label}"
                    conclusion += f" ({pts/gp:.2f} points per game). This is production evidence, not proof of independent team impact."
                    facts.append(f"Official NHL club-season statistics: {profile.display_name}, {pts:g} points in {gp:g} games ({target}).")
                    limitations = [x for x in limitations if "current-season production" not in x.casefold()]
                    limitations.append("Deployment and defensive impact remain unverified.")
                    official = {"statistical_evidence": {"contract": "canonical_player_statistical_evidence", "source": "official_nhl_club_stats", "target_season": target, "season_series": [{"season": target, "gp": gp, "points": pts, "goals": club_row.get("goals"), "assists": club_row.get("assists")}]}, "source": "official_nhl_club_stats"}
                    if isinstance(player_bundle, dict):
                        player_bundle["official_player_record"] = official
                        player_bundle["fallback_source"] = "official_nhl_club_stats"
            except (ImportError, ValueError, TypeError, KeyError, OSError) as exc:
                if isinstance(player_bundle, dict):
                    player_bundle["club_stats_fallback_error"] = type(exc).__name__
    if assessment["kind"] == "current_evidence":
        from Knowledge.Intelligence.Public.player_evidence import authoritative_statistical_view
        view = authoritative_statistical_view(official) if isinstance(official, dict) and official else {}
        series = view.get("season_series", [])
        target = str(view.get("target_season") or "")
        current = next((row for row in series if str(row.get("season") or "").replace("-", "").startswith(target[:4]) and target), None)
        if current and isinstance(current.get("gp"), (int, float)) and current["gp"] > 0:
            gp, points = current["gp"], current.get("points")
            goals, assists = current.get("goals"), current.get("assists")
            pieces = [f"{gp:g} games"]
            for label, val in (("goals", goals), ("assists", assists), ("points", points)):
                if isinstance(val, (int, float)): pieces.append(f"{val:g} {label}")
            conclusion = f"{profile.display_name} has verified {target} NHL regular-season production: " + ", ".join(pieces) + "."
            if isinstance(points, (int, float)):
                conclusion += f" That is {points/gp:.2f} points per game over the observed sample."
            previous = next((row for row in series if row is not current and isinstance(row.get("gp"), (int, float)) and row["gp"] > 0 and isinstance(row.get("points"), (int, float))), None)
            if previous and isinstance(points, (int, float)):
                prior_rate = previous["points"] / previous["gp"]
                delta = points/gp-prior_rate
                conclusion += f" The preceding observed {previous.get('season')} season averaged {prior_rate:.2f} points per game (difference {delta:+.2f})."
            conclusion += " This measures production, not independent evidence of deployment, defensive impact or causation."
            limitations = [x for x in limitations if "current" not in x.casefold() and "performance" not in x.casefold()]
            limitations.append("Role, ice time and team impact require separately verified deployment evidence.")
        else:
            conclusion = f"{profile.display_name} is identified, but no verified {target or 'target-season'} NHL regular-season production was returned. Earlier season totals cannot be presented as current-season performance."
            limitations.append("Current-season player production not verified in the acquired official record.")
    if dated_news:
        for item in dated_news[:3]:
            facts.append(f"Dated player-specific report: {item.get('title')} ({item.get('published_at') or item.get('published') or 'date supplied by source'}).")
        # Dated reports supplement official production; they must not replace
        # a verified statistical conclusion or erase an evidence limitation.
    missing = list(player_bundle.get("missing", [])) if isinstance(player_bundle, dict) else ["athena_request_evidence_bundle"]
    answer = response(
        intent="public_player_investigation",
        title=f"{profile.display_name}: {assessment['kind'].replace('_', ' ')}",
        engine_conclusion=conclusion,
        natural_language_response=conclusion,
        observed_facts=facts,
        known_limitations=limitations,
        confidence=(0.76 if assessment["kind"] == "current_evidence" and current and isinstance(current.get("gp"), (int, float)) and current["gp"] > 0 else min(assessment["confidence"], 0.48) if assessment["kind"] == "current_evidence" else max(assessment["confidence"], 0.72 if official else assessment["confidence"])),
        developer=developer_info(
            "public_player_investigation", getattr(context, "files_loaded", []),
            knowledge_used=["public_entity_registry"] + (["official_nhl_player_record"] if official else ["public_player_profile_seed"]) + (["dated_identity_matched_player_news"] if dated_news else []),
            intelligence_used=["question_scoped_public_player_reasoning", "athena_request_evidence_bundle"],
            files_read=["Athena/evidence_bundle.py", "Knowledge/Intelligence/Public/player_evidence.py", "Reasoning/public_player_questions.py"],
            missing=missing,
        ),
    )
    answer["developer"]["identity_resolution"] = match.to_dict()
    answer["developer"]["public_player_profile"] = profile.to_dict()
    answer["developer"]["request_evidence"] = player_bundle
    return answer

