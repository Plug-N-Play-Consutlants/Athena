"""Named-player historical stature investigation; evidence inventory, not verdict."""
from __future__ import annotations
from typing import Any


def execute_historical_stature(context: Any, question: str) -> dict:
    from Athena.public_identity import resolve_public_player
    from Knowledge.Intelligence.Public.public_player_profiles import profile_for_entity
    from Knowledge.Intelligence.Public.player_evidence import player_evidence
    from Athena.player_assessment import assess_player
    from Scout.conversation.responses import response, developer_info

    match = resolve_public_player(question)
    profile = profile_for_entity(match.entity) if match is not None and match.entity is not None else None
    if profile is None:
        # Full natural-language questions are not themselves qualified identity
        # strings. Recover only a unique profile already recognized by Athena.
        from Athena.intent_planner import _public_player_profiles_for
        profiles = _public_player_profiles_for(question)
        if len(profiles) == 1:
            profile = profiles[0]
    if profile is None:
        return response(intent="public_player_historical_stature_gap", title="Historical player identity unresolved",
                        engine_conclusion="The requested player's identity is not verified; a historical classification would be speculative.",
                        observed_facts=[], known_limitations=["Qualified public player identity is required."], confidence=0.25,
                        developer=developer_info("public_player_historical_stature_gap", getattr(context, "files_loaded", []), missing=["qualified_player_identity"]))
    evidence = player_evidence(profile.display_name, team=profile.team, position=profile.position)
    assessment = assess_player(evidence) if evidence else {}
    stature = assessment.get("historical_stature") or {}
    observations = list(stature.get("supporting_observations") or [])
    tests = list(stature.get("unresolved_tests") or [])
    career = assessment.get("career_legacy")
    current = assessment.get("current_tier")
    name = profile.display_name
    opening = (f"{name}'s historical stature is not determined by the current three-season scoring tier. "
               f"The observed scoring-window label ({current or 'unrated'}) and career production label "
               f"({career or 'unrated'}) are separate measures, not a generational verdict. ")
    if observations:
        opening += "Verified historical observations: " + " ".join(observations[:6]) + " "
    opening += ("A generational classification requires weighing era-relative dominance, sustained excellence, "
                "position-specific impact, and contrary evidence. The current inventory cannot complete those tests. "
                "That is an evidence limitation, not a conclusion that the player is or is not generational.")
    # Completion is assessed against the question, not inferred from a successful
    # specialist invocation. Missing evidence is never silently marked reviewed.
    requirements = [
        {"dimension": "historical_production_and_awards", "state": "supported" if observations else "unresolved",
         "basis": "verified_individual_evidence" if observations else "no_verified_observations"},
        {"dimension": "era_adjusted_peer_comparison", "state": "unresolved", "basis": "peer_distribution_not_acquired"},
        {"dimension": "sustained_dominance", "state": "unresolved", "basis": "era_relative_longevity_not_established"},
        {"dimension": "two_way_impact", "state": "unresolved", "basis": "defensive_evidence_not_acquired"},
        {"dimension": "injury_and_availability", "state": "unresolved", "basis": "dated_health_evidence_not_acquired"},
        {"dimension": "counterevidence_and_verdict", "state": "unresolved", "basis": "comparative_tests_incomplete"},
    ]
    completion = {"state": "partial", "requirements": requirements,
                  "unresolved": [item["dimension"] for item in requirements if item["state"] == "unresolved"]}
    result = response(intent="public_player_historical_stature", title=f"{name}: historical stature assessment",
                    engine_conclusion=opening, natural_language_response=opening,
                    observed_facts=observations,
                    known_limitations=tests or ["Historical comparison evidence has not been verified."],
                    confidence=0.64 if observations else 0.38,
                    developer=developer_info("public_player_historical_stature", getattr(context, "files_loaded", []),
                        knowledge_used=["nhl_player_evidence", "historical_stature_inventory"],
                        intelligence_used=["historical_stature_evidence_boundary"],
                        files_read=["Athena/historical_stature.py", "Athena/player_assessment.py"],
                        missing=["era_adjusted_peers", "verified_defensive_impact", "dated_injury_cohorts"]))
    result["inquiry_completion"] = completion
    return result
