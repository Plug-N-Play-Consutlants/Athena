"""Evidence-bounded player development inquiry, distinct from live news routing."""
from __future__ import annotations
import re
from typing import Any, Dict, List

def _named_player(question: str, players: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    q = question.casefold()
    matches = [p for p in players if p.get("name") and
               re.search(r"(?<!\\w)" + re.escape(str(p["name"]).casefold()) + r"(?!\\w)", q)]
    return max(matches, key=lambda p: len(str(p["name"]))) if matches else None

def _historical_levels(landing: Dict[str, Any]) -> List[Dict[str, Any]]:
    # The public NHL landing feed can contain multiple season/league observations.
    # Keep them as observations, not explanations for promotion timing.
    rows = landing.get("seasonTotals") or []
    events = []
    for row in rows:
        if not isinstance(row, dict): continue
        season = row.get("season")
        league = row.get("leagueAbbrev") or row.get("league") or ""
        if not (season and league): continue
        events.append({"season": season, "league": league,
                       "team": row.get("teamName") or row.get("teamCommonName") or "",
                       "games_played": row.get("gamesPlayed"),
                       "goals": row.get("goals"), "assists": row.get("assists"),
                       "points": row.get("points"),
                       "game_type": row.get("gameTypeId")})
    return events

def analyze_player_development(player: Dict[str, Any], *, history=None, baselines=None, opportunity=None) -> Dict[str, Any]:
    from Reasoning.Players import build_player_intelligence
    profile = build_player_intelligence(player, history=history, baselines=baselines, opportunity=opportunity)
    name = str(player.get("name") or "The player")
    age = player.get("age")
    age_phrase = f" at age {age}" if isinstance(age, int) else ""
    gp = player.get("games_played")
    lines = [f"{name}: development pathway and NHL projection",
             f"{name} is identified as {player.get('relationship') or 'a player'}{age_phrase}. "
             "NHL roster attainment and career progression are observable evidence; neither establishes why promotion happened at that time."]
    if history:
        leagues = list(dict.fromkeys(str(x.get("league")) for x in history if x.get("league")))
        lines.append("Recorded development levels: " + ", ".join(leagues) +
                     ". These are career observations, not evidence that any particular level caused a delay.")
    else:
        lines.append("Longitudinal NCAA/AHL/junior season evidence is not established on this path; Athena cannot reconstruct the full pathway.")
    if isinstance(gp, (int, float)):
        lines.append(f"Current club-stat coverage records {gp:g} NHL games. " +
                     ("That is an immature statistical sample, not proof that roster/deployment evidence is meaningless."
                      if gp < 20 else "Statistical stability still depends on role, conditions and representativeness."))
    else:
        lines.append("Current NHL games-played evidence is unavailable on this acquisition path.")
    lines.append("Comparative baseline: " + (
        "A relevant full-population comparison cohort is available for evaluation."
        if baselines else
        "No validated age-at-debut/attainment cohort is available here. Comparing only players who made the NHL would exclude non-attainers and bias the result; therefore Athena cannot call this debut early, average or late."
    ))
    lines.append("Opportunity versus capability: " + (
        "Documented roster constraints can be assessed separately from capability."
        if opportunity else
        "Depth-chart congestion, coaching fit, waiver/contract constraints and earlier NHL readiness remain competing hypotheses, not established causes."
    ))
    lines.append("Projection: " + (
        "The observed NHL evidence can update the historical development profile, but does not yet justify a precise role probability or ceiling."
        if history or isinstance(gp,(int,float)) and gp > 0 else
        "Without sufficient historical and current-role evidence, a specific NHL role or ceiling would be speculative."
    ))
    return {"name": name, "profile": profile, "text": "\n\n".join(lines),
            "history_count": len(history or []), "baseline_count": len(baselines or [])}

def execute_player_development(context: Any, question: str) -> Dict[str, Any]:
    from Knowledge.Organizations.nhl_roster_evidence import acquire_team_player_evidence
    from Scout.conversation.responses import response, developer_info
    from Providers.NHL.nhl_client import NHLClient
    from Athena.public_identity import resolve_public_player
    teams = ["TOR"] if any(t in question.casefold() for t in ("leafs","toronto")) else ["TOR"]
    acquisition_errors = []
    selected = None
    for team in teams:
        org = acquire_team_player_evidence(team)
        acquisition_errors.extend(org.get("acquisition_errors") or [])
        selected = _named_player(question, list(org.get("roster") or []) + list(org.get("prospects") or []))
        if selected: break
    # A name in the user prompt is not sufficient proof of an NHL identity.
    if selected is None:
        match = resolve_public_player(question)
        if match is not None and match.entity is not None:
            from Knowledge.Intelligence.Public.public_player_profiles import profile_for_entity
            profile = profile_for_entity(match.entity)
            if profile is not None:
                selected = {"name": profile.display_name, "relationship": "public_profile"}
    if selected is None:
        message = ("The requested player's identity could not be verified in the available player evidence. "
                   "Athena cannot substitute unrelated college-hockey news for a player-development assessment.")
        return response(intent="public_player_development", title="Player development evidence gap",
                        engine_conclusion=message, natural_language_response=message,
                        observed_facts=[], known_limitations=acquisition_errors + ["Verified player identity is required."],
                        confidence=.3, developer=developer_info("public_player_development",getattr(context,"files_loaded",[]),
                            missing=["verified_player_identity"]))
    history = []
    pid = str(selected.get("nhl_player_id") or "")
    if pid:
        try:
            landing = NHLClient().get_player_landing(pid)
            if isinstance(landing, dict):
                history = _historical_levels(landing)
                draft = landing.get("draftDetails")
                if isinstance(draft, dict): selected["draft"] = draft
        except Exception as exc:
            acquisition_errors.append(f"player_landing: {type(exc).__name__}: {exc}")
    assessment = analyze_player_development(selected,history=history)
    limitations = list(assessment["profile"].get("uncertainty") or []) + acquisition_errors
    answer = response(intent="public_player_development",
                      title=f"{selected['name']}: development and projection",
                      engine_conclusion=assessment["text"], natural_language_response=assessment["text"],
                      observed_facts=[f"Verified player: {selected['name']}.",
                                      f"Recorded season/league observations: {len(history)}."],
                      known_limitations=limitations, confidence=.65 if history else .45,
                      developer=developer_info("public_player_development",getattr(context,"files_loaded",[]),
                          knowledge_used=["nhl_current_roster","nhl_prospects","nhl_player_landing"],
                          intelligence_used=["player_intelligence","development_pathway","sample_vs_context_sufficiency"],
                          missing=["validated_full_population_baselines","verified_opportunity_context"]))
    answer["developer"]["player_intelligence"] = assessment["profile"]
    answer["developer"]["development_evidence"] = {"history": history, "player": selected}
    return answer
