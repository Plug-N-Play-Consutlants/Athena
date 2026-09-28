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
    if dated_news:
        for item in dated_news[:3]:
            facts.append(f"Dated player-specific report: {item.get('title')} ({item.get('published_at') or item.get('published') or 'date supplied by source'}).")
        if assessment["kind"] == "current_evidence":
            conclusion = (f"Athena found dated reporting tied specifically to {profile.display_name}. "
                          "Those reports are attached as current evidence below; they should be interpreted alongside the official NHL record rather than the seeded identity profile alone.")
    missing = list(player_bundle.get("missing", [])) if isinstance(player_bundle, dict) else ["athena_request_evidence_bundle"]
    answer = response(
        intent="public_player_investigation",
        title=f"{profile.display_name}: {assessment['kind'].replace('_', ' ')}",
        engine_conclusion=conclusion,
        natural_language_response=conclusion,
        observed_facts=facts,
        known_limitations=limitations,
        confidence=max(assessment["confidence"], 0.72 if official else assessment["confidence"]),
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

