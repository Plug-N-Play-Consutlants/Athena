"""Public-facing answer helpers for PIF-1.

Drop 4e37 reconnects public identity routing to Athena's deeper reasoning
pipeline. Seed profiles remain the identity substrate; they are no longer the
final answer when richer player intelligence is available.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from Knowledge.Intelligence.Entities.entity_registry import PublicEntity
from Knowledge.Intelligence.Public.public_player_profiles import PublicPlayerProfile, profile_for_entity
from Knowledge.Intelligence.Public.public_team_profiles import PublicTeamProfile, profile_for_team_entity
from Scout.conversation.responses import developer_info, response


def _entity_label(entity: PublicEntity) -> str:
    label = entity.metadata.get("disambiguation_label") if isinstance(entity.metadata, dict) else None
    return str(label or f"{entity.canonical_name} — {entity.position or entity.entity_type} — {entity.team or entity.league}")


def _entity_prompt(entity: PublicEntity) -> str:
    team = entity.team or ""
    if entity.entity_id == "nhl.player.sebastian_aho_car":
        return "Tell me about Finnish Sebastian Aho"
    if entity.entity_id == "nhl.player.sebastian_aho_swe":
        return "Tell me about Swedish Sebastian Aho"
    return "Tell me about " + " ".join(part for part in [entity.canonical_name, team] if part).strip()


def _profile_matches_public_entity(evaluation: Dict[str, Any], profile: PublicPlayerProfile) -> bool:
    """Prevent seeded public disambiguation from merging two same-name players."""
    player = evaluation.get("player") if isinstance(evaluation.get("player"), dict) else {}
    eval_team = str(player.get("nhl_team") or "").upper()
    public_team = (profile.team or "").upper()
    if profile.entity_id == "nhl.player.sebastian_aho_swe":
        return False
    if public_team and "/" not in public_team and eval_team and eval_team != public_team:
        return False
    return True


def _build_reasoned_player_brief(profile: PublicPlayerProfile, question: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Any]]:
    """Run the existing player intelligence + reasoning + executive brief stack.

    This is intentionally best-effort. If the richer local output files do not
    contain this player, PIF falls back to the public seed profile rather than
    inventing facts.
    """
    try:
        from Intelligence.Player.player_intelligence import evaluate_player
        from Reasoning.adapters.player_evidence_adapter import build_player_profile_from_evaluation
        from Reasoning.reasoning_engine import ReasoningEngine
        from Reasoning.composition.executive_brief import ExecutiveBriefComposer

        # The seeded public display name is the safest bridge into the older
        # player evidence outputs. Same-name edge cases are guarded below.
        evaluation = evaluate_player(profile.display_name, mode="public")
        if evaluation.get("status") != "available":
            return None, evaluation, None
        if not _profile_matches_public_entity(evaluation, profile):
            evaluation.setdefault("developer", {}).setdefault("missing", []).append("public_entity_does_not_match_local_player_intelligence_row")
            return None, evaluation, None
        player_profile = build_player_profile_from_evaluation(evaluation, fallback_name=profile.display_name)
        assessment = ReasoningEngine().reason_about_player(player_profile, evaluation)
        brief = ExecutiveBriefComposer().build_player_brief(
            assessment,
            evaluation=evaluation,
            question=question or profile.display_name,
            mode="public",
        )
        return brief, evaluation, assessment
    except Exception as ex:  # pragma: no cover - Scout fallback keeps demo usable
        return None, {"status": "reasoning_error", "developer": {"error": str(ex)}}, None


def _brief_sections_as_facts(brief: Dict[str, Any]) -> List[str]:
    """Expose concise evidence facts without duplicating the rendered brief body."""
    facts: List[str] = []
    evidence_counts = brief.get("evidence_counts") if isinstance(brief.get("evidence_counts"), dict) else {}
    for label, count in evidence_counts.items():
        facts.append(f"{str(label).replace('_', ' ').title()} evidence available: {count}.")
    for item in brief.get("supporting_evidence") or []:
        text = _publicize_brief_text(str(item))
        if text and text not in facts:
            facts.append(text)
    if not facts:
        for section in brief.get("sections") or []:
            heading = section.get("heading")
            body = _publicize_brief_text(section.get("body") or "")
            if body:
                facts.append(f"{heading}: {body}" if heading else body)
    return facts[:6]


def _set_public_surface(answer: Dict[str, object], text: str) -> Dict[str, object]:
    """Collapse all legacy public-answer aliases onto the same public text."""
    public = str(text or "").strip()
    answer["public_comment"] = public
    answer["natural_language_response"] = public
    answer["response_text"] = public
    answer["scout_message"] = public
    answer["display_contract"] = "public_comment_only"
    return answer


def _publicize_brief_text(text: str) -> str:
    """Keep older executive brief output public-first when rendered in Public."""
    if not text:
        return text
    replacements = {
        "fantasy roster context": "public context",
        "Fantasy roster context": "Public context",
        "fantasy context": "public context",
        "Fantasy context": "Public context",
        "Fantasy Impact": "Context Impact",
        "Fantasy Role": "Public Role",
        "fantasy impact": "context impact",
        "Fantasy profile evidence": "Public profile evidence",
        "fantasy profile evidence": "public profile evidence",
        "Fantasy evidence": "Context evidence",
        "fantasy evidence": "context evidence",
        "core fantasy asset": "core asset",
        "Core Fantasy Asset": "Core Asset",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text




def _fmt_number(value: Any, places: int = 3) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    return f"{number:.{places}f}"


def _production_sentence(evaluation: Optional[Dict[str, Any]]) -> str:
    if not isinstance(evaluation, dict):
        return ""
    production = ((evaluation.get("profiles") or {}).get("production") or {}) if isinstance(evaluation.get("profiles"), dict) else {}
    if not production.get("available"):
        return ""
    points = production.get("points")
    goals = production.get("goals")
    assists = production.get("assists")
    games = production.get("games_played")
    ppg = _fmt_number(production.get("points_per_game"), 3)
    band = str(production.get("production_band") or "").replace("_", " ")
    pieces = []
    if points not in (None, "") and games not in (None, ""):
        pieces.append(f"current local production is {int(float(points))} points in {int(float(games))} games")
    if goals not in (None, "") and assists not in (None, ""):
        pieces.append(f"with a {int(float(goals))}-{int(float(assists))} goal-assist split")
    if ppg:
        pieces.append(f"{ppg} points per game")
    if band:
        pieces.append(f"classified locally as {band} production")
    return "The current statistical snapshot says " + ", ".join(pieces) + "." if pieces else ""


def _compose_public_player_copy(profile: PublicPlayerProfile, question: str, fallback: str = "", evaluation: Optional[Dict[str, Any]] = None) -> str:
    """Return analyst-style public prose instead of retrieval/internal assessment prose."""
    q = (question or "").lower()
    legacy = any(term in q for term in ["legacy", "career", "evolved", "throughout", "history", "all-time", "all time"])
    current = any(term in q for term in ["right now", "currently", "current", "today", "this season", "how good"])

    opening_bits = []
    if profile.draft:
        opening_bits.append(profile.draft)
    if profile.role:
        opening_bits.append(profile.role)
    opening = f"{profile.display_name} is {profile.role}." if profile.role else f"{profile.display_name} is a {profile.position} for {profile.team}."
    if profile.draft:
        opening = f"{profile.display_name} entered the NHL as the {profile.draft} and has developed into {profile.role}."

    paragraphs: List[str] = [opening]

    achievement_parts: List[str] = []
    if profile.awards:
        achievement_parts.append("major résumé markers include " + ", ".join(profile.awards[:8]))
    if profile.career_identity:
        achievement_parts.append(profile.career_identity)
    if achievement_parts:
        achievement_text = "; ".join(part.rstrip(".") for part in achievement_parts)
        paragraphs.append("From an analytical lens, " + achievement_text + ".")

    style = profile.style
    if profile.physical_profile:
        style = f"{profile.physical_profile} His playing profile is built around {profile.style}" if profile.style else profile.physical_profile
    if style:
        paragraphs.append(style.rstrip(".") + ".")

    prod = _production_sentence(evaluation)
    if prod:
        paragraphs.append(prod)

    if profile.current_context:
        paragraphs.append(profile.current_context)

    if profile.international_context and (legacy or current or "international" in q or profile.display_name == "Auston Matthews"):
        paragraphs.append(profile.international_context)

    notes = list(profile.analytical_notes or [])
    if notes:
        if current:
            paragraphs.append("Current read: " + " ".join(notes[:3]))
        elif legacy:
            paragraphs.append("Legacy read: " + " ".join(notes[:3]))
        else:
            paragraphs.append("Analytical read: " + " ".join(notes[:2]))
    elif profile.career_notes:
        paragraphs.append("Useful context: " + " ".join(profile.career_notes[:3]))

    if profile.fantasy_context and any(term in q for term in ["fantasy", "fantrax", "trade", "keeper", "dynasty", "value", "how good"]):
        paragraphs.append("Fantasy/value lens: " + profile.fantasy_context)

    if fallback:
        clean = _publicize_brief_text(fallback)
        forbidden = ["Athena is combining", "no longer assessed as", "evidence available", "Player Intelligence", "PIF Build", "current local evidence"]
        if clean and not any(term.lower() in clean.lower() for term in forbidden):
            paragraphs.append(clean)

    limitations = [item for item in profile.known_limitations if "PIF" not in item and "Build" not in item]
    if limitations:
        paragraphs.append("Sharper live analysis still needs: " + limitations[0])

    return "\n\n".join(part.strip() for part in paragraphs if part and part.strip())

def _clean_public_copy(text: str) -> str:
    return (text or "").replace(" nHL", " NHL").replace(" are NHL franchise", " is an NHL franchise").replace("..", ".")


def _normalize_public_question(question: str) -> str:
    text = (question or "").lower()
    text = re.sub(r"\bleaf['’]?s\b", "leafs", text)
    text = re.sub(r"\bmaple leaf['’]?s\b", "maple leafs", text)
    return text


def _possessive_name(name: str) -> str:
    clean = str(name or "This team").strip() or "This team"
    return clean + "'" if clean.endswith("s") else clean + "'s"


def _compose_public_team_copy(profile: PublicTeamProfile, question: str, assessment: Any = None) -> str:
    q = _normalize_public_question(question)
    weak_terms = ["weakness", "weaknesses", "weak spot", "weak spots", "weak", "flaw", "flaws", "problem", "problems", "struggle", "struggled", "struggling", "hold them back"]
    asks_weakness = any(term in q for term in weak_terms)
    asks_quality = asks_weakness or any(term in q for term in ["how good", "contender", "strong", "why", "ceiling", "outlook", "analyze"])

    if "defens" in q and ("oilers" in q or "edmonton" in q):
        return (
            "Edmonton's defensive problem is not explained by a lack of offensive talent. It is a roster-balance and support-structure problem: the public profile identifies an elite McDavid/Draisaitl offensive core, while the risk profile points to defensive-zone structure, goaltending volatility, blue-line depth, and supporting-cast balance.\n\n"
            "The analytical distinction matters: high-end centers can drive possession and scoring, but they do not automatically solve defensive-zone exits, matchup depth, penalty killing, save-percentage volatility, or the quality of the second and third defensive pairs. On an offense-first contender, every weakness behind the stars becomes more visible because the championship expectation is higher.\n\n"
            "So the read is: Edmonton has enough top-end talent to contend, but its reliability depends on the support layer. Without live roster, goalie, injury, deployment, and recent performance feeds, Athena should stop at that structural conclusion rather than inventing a precise current metric."
        )

    if asks_weakness:
        risks = list(profile.risks or [])
        strengths = list(profile.strengths or [])
        named_risks = ", ".join(risks) if risks else "the support layer around the core"
        named_strengths = ", ".join(strengths) if strengths else "the team's strongest public traits"
        paragraphs = [
            f"{_possessive_name(profile.display_name)} main weakness is not a lack of headline talent; it is whether the supporting structure is strong enough to make that talent hold up in high-leverage games.",
            f"The clearest risk areas in the current public profile are: {named_risks}.",
            f"That matters because the positive case is built around {named_strengths}. If the depth, defensive structure, health, cap flexibility, or postseason execution behind that core is not good enough, the team can look dangerous on paper while still being vulnerable when matchups tighten.",
        ]
        if profile.analytical_read:
            paragraphs.append(f"Analytical read: {profile.analytical_read}")
        if profile.competitive_identity:
            paragraphs.append(f"Competitive context: {profile.competitive_identity}")
        limitation = next((item for item in profile.known_limitations if item), "")
        if limitation:
            paragraphs.append("Sharper current weakness analysis still needs live roster, injury, deployment, goalie, cap, and recent-performance evidence.")
        return _clean_public_copy("\n\n".join(paragraphs))

    paragraphs: List[str] = []
    if profile.identity:
        identity = profile.identity[0].lower() + profile.identity[1:]
        if identity.lower().startswith("nhl franchise"):
            identity = "an " + identity.upper()[:3] + identity[3:]
        paragraphs.append(f"{profile.display_name} is {identity}.")
    else:
        paragraphs.append(f"{profile.display_name} is an NHL organization.")
    if profile.history:
        paragraphs.append(profile.history)

    if profile.competitive_identity or profile.analytical_read:
        paragraphs.append("Competitive identity: " + (profile.competitive_identity or profile.analytical_read))

    if profile.core_players:
        paragraphs.append("Core players to anchor the evaluation: " + ", ".join(profile.core_players) + ".")

    if profile.strengths:
        paragraphs.append("Why they can be good: " + ", ".join(profile.strengths) + ".")
    elif assessment is not None and getattr(assessment, "strengths", None):
        paragraphs.append("Why they can be good: " + assessment.strengths.conclusion)

    if profile.risks:
        paragraphs.append("What can hold them back: " + ", ".join(profile.risks) + ".")
    elif assessment is not None and getattr(assessment, "weaknesses", None):
        paragraphs.append("What can hold them back: " + assessment.weaknesses.conclusion)

    if profile.analytical_read:
        label = "Analytical read" if asks_quality else "Current lens"
        paragraphs.append(f"{label}: {profile.analytical_read}")
    elif profile.organizational_context:
        paragraphs.append("Current lens: " + profile.organizational_context)

    if profile.roster_context and not profile.core_players:
        paragraphs.append("Roster context: " + profile.roster_context)

    limitation = next((item for item in profile.known_limitations if item), "")
    if limitation:
        paragraphs.append("Sharper live team analysis still needs: " + limitation)

    return _clean_public_copy("\n\n".join(str(part).strip() for part in paragraphs if str(part).strip()))

def _disambiguation_profile_summary(entity: PublicEntity) -> str:
    profile = profile_for_entity(entity)
    if profile is not None:
        pieces = [
            f"{profile.display_name} — {profile.position} / {profile.team}",
            profile.public_value,
            profile.career_identity,
        ]
        return ": ".join(part for part in pieces if part)
    return _entity_label(entity)


def _disambiguation_card_label(entity: PublicEntity) -> str:
    if entity.entity_id == "nhl.player.sebastian_aho_car":
        return "Finnish Aho"
    if entity.entity_id == "nhl.player.sebastian_aho_swe":
        return "Swedish Aho"
    return entity.position or entity.entity_type


def disambiguation_answer(ctx, question: str, entities: List) -> Dict[str, object]:
    options = []
    facts = []
    for match in entities:
        candidates = getattr(match, "candidates", None) or []
        if candidates:
            options.extend(candidates)
        elif getattr(match, "entity", None) is not None:
            options.append(match.entity)
    seen = set()
    unique = []
    for entity in options:
        if entity.entity_id not in seen:
            seen.add(entity.entity_id)
            unique.append(entity)
    for entity in unique:
        facts.append(_disambiguation_profile_summary(entity))

    cards = []
    for entity in unique:
        cards.append({
            "label": _disambiguation_card_label(entity),
            "value": _entity_label(entity),
            "prompt": _entity_prompt(entity),
            "action": "ask_prompt",
        })

    natural = (
        "There is more than one public sports profile matching that name. "
        "Here are the candidates I found; choose one to continue with the correct player.\n\n"
        + "\n".join(f"• {fact}" for fact in facts)
    )
    answer = response(
        intent="public_entity_disambiguation",
        title="Which Sebastian Aho?" if "sebastian aho" in question.lower() else "Which player did you mean?",
        engine_conclusion="Athena found more than one public sports entity matching that name and needs the user to choose before reasoning.",
        observed_facts=facts or ["Multiple candidate entities were found."],
        known_limitations=["Follow-up entity selection is card-driven in this build; longer conversation memory arrives later."],
        confidence=0.92,
        cards=cards,
        developer=developer_info(
            "public_entity_disambiguation",
            getattr(ctx, "files_loaded", []),
            knowledge_used=["public_entity_registry", "public_identity_graph"],
            intelligence_used=["entity_disambiguation", "public_profile_candidate_summaries", "clickable_disambiguation_cards"],
            files_read=["Knowledge/Intelligence/Entities/entity_registry.py", "Knowledge/Intelligence/Public/public_player_profiles.py"],
            missing=["persistent_follow_up_entity_memory"],
        ),
    )
    return _set_public_surface(answer, natural)


def player_profile_answer(ctx, profile: PublicPlayerProfile, question: str) -> Dict[str, object]:
    brief, evaluation, assessment = _build_reasoned_player_brief(profile, question)

    observed = [
        f"Identity: {profile.display_name} is a {profile.position} for {profile.team}.",
        f"Public role: {profile.role}.",
        f"Style: {profile.style}.",
        f"Draft context: {profile.draft or 'not seeded yet'}.",
    ]
    observed.extend(profile.career_notes[:5])
    if profile.awards:
        observed.append("Awards/legacy signals: " + ", ".join(profile.awards) + ".")

    cards = [
        {"label": "Player", "value": profile.display_name},
        {"label": "Team", "value": profile.team},
        {"label": "Position", "value": profile.position},
        {"label": "Public value", "value": profile.public_value},
    ]

    if brief:
        title = brief.get("title") or f"{profile.display_name} — {profile.position} / {profile.team}"
        confidence = brief.get("confidence", 0.84)
        cards = list(brief.get("cards") or cards)
        observed = _brief_sections_as_facts(brief) or observed
        conclusion = _publicize_brief_text(brief.get("executive_summary") or profile.career_identity)
        natural = _compose_public_player_copy(profile, question, fallback=conclusion, evaluation=evaluation)
        intelligence_used = [
            "pif_public_profile_answer",
            "player_intelligence",
            "reasoning_engine",
            "executive_brief_composer",
            "reasoning_reintegration",
        ]
        missing = (evaluation or {}).get("developer", {}).get("missing", []) if isinstance(evaluation, dict) else []
        known_limits = list((evaluation or {}).get("limitations") or []) if isinstance(evaluation, dict) else []
        known_limits.extend(profile.known_limitations)
    else:
        title = f"{profile.display_name} — {profile.position} / {profile.team}"
        confidence = 0.80
        conclusion = profile.career_identity
        natural = _compose_public_player_copy(profile, question, fallback=conclusion, evaluation=evaluation)
        intelligence_used = ["pif_public_profile_answer", "seed_profile_fallback"]
        missing = ["local_player_reasoning_match"]
        known_limits = list(profile.known_limitations) + ["PIF public seed profile used because full local player reasoning was unavailable for this entity."]

    answer = response(
        intent="public_player_profile",
        title=title,
        engine_conclusion=conclusion,
        observed_facts=[_publicize_brief_text(str(item)) for item in observed],
        known_limitations=known_limits,
        confidence=confidence,
        cards=cards,
        developer=developer_info(
            "public_player_profile",
            getattr(ctx, "files_loaded", []),
            knowledge_used=["public_entity_registry", "public_player_profile_seed", "public_identity_graph", "local_player_outputs"],
            intelligence_used=intelligence_used,
            files_read=[
                "Knowledge/Intelligence/Public/public_player_profiles.py",
                "Output/player_master.json",
                "Output/player_production.json",
                "Output/player_profiles.json",
                "Output/player_contracts.json",
            ],
            missing=missing,
        ),
    )
    _set_public_surface(answer, natural)
    answer["developer"]["public_player_profile"] = profile.to_dict()
    if isinstance(evaluation, dict):
        answer["developer"]["player_evaluation"] = evaluation
    if assessment is not None:
        answer["developer"]["reasoning_assessment"] = assessment.as_dict() if hasattr(assessment, "as_dict") else str(assessment)
    if brief:
        answer["developer"]["executive_brief"] = brief
    return answer


def team_profile_answer(ctx, profile: PublicTeamProfile, question: str) -> Dict[str, object]:
    try:
        from Reasoning.team_reasoning_engine import TeamReasoningEngine

        assessment = TeamReasoningEngine().reason_about_public_team(profile, question)
    except Exception as ex:  # pragma: no cover - keeps Scout resilient during partial installs
        assessment = None
        reasoning_error = str(ex)
    else:
        reasoning_error = ""

    if assessment is not None:
        sections = [
            assessment.historical_context,
            assessment.organizational_identity,
            assessment.strengths,
            assessment.weaknesses,
            assessment.current_direction,
            assessment.future_outlook,
        ]
        observed = [
            f"{section.name}: {section.conclusion}"
            for section in sections
        ]
        natural = _compose_public_team_copy(profile, question, assessment=assessment)
        conclusion = assessment.executive_summary
        confidence = assessment.confidence
        known_limitations = assessment.limitations
        intelligence_used = ["pif_public_team_profile_answer", "team_reasoning_engine", "team_narrative_seed"]
        missing = ["live_roster_feed", "salary_cap_feed", "injury_feed", "event_intelligence_feed"]
    else:
        observed = [
            f"Identity: {profile.display_name} ({profile.abbreviation}) is an {profile.league} team in the {profile.conference} Conference / {profile.division} Division.",
            f"Organizational context: {profile.organizational_context}",
            f"Roster context: {profile.roster_context}",
            "Public team route selected; provider-specific league ownership data is excluded unless explicitly requested.",
        ]
        natural = _compose_public_team_copy(profile, question)
        conclusion = profile.identity
        confidence = 0.76
        known_limitations = list(profile.known_limitations) + ["PIF Build team profiles are seed context; live standings, cap, injuries and transaction feeds arrive later."]
        intelligence_used = ["pif_public_team_profile_answer", "team_narrative_seed"]
        missing = ["team_reasoning_engine", "live_roster_feed", "salary_cap_feed", "injury_feed", "event_intelligence_feed"]
        if reasoning_error:
            missing.append(f"team_reasoning_error: {reasoning_error}")

    cards = [
        {"label": "Team", "value": profile.display_name},
        {"label": "Division", "value": profile.division or "seed pending"},
        {"label": "Conference", "value": profile.conference or "seed pending"},
        {"label": "Context", "value": ", ".join(profile.public_questions[:3]) if profile.public_questions else "seeded"},
    ]
    answer_title = f"{profile.display_name} — {profile.abbreviation}"
    q_title = _normalize_public_question(question)
    if any(term in q_title for term in ["weakness", "weaknesses", "weak spot", "weak spots", "flaw", "flaws", "problem", "problems", "struggle", "struggled", "struggling"]):
        answer_title = f"{profile.display_name} weakness analysis"

    answer = response(
        intent="public_team_profile",
        title=answer_title,
        engine_conclusion=conclusion,
        observed_facts=observed,
        known_limitations=known_limitations,
        confidence=confidence,
        cards=cards,
        developer=developer_info(
            "public_team_profile",
            getattr(ctx, "files_loaded", []),
            knowledge_used=["public_entity_registry", "public_team_profile_seed"],
            intelligence_used=intelligence_used,
            files_read=["Knowledge/Intelligence/Public/public_team_profiles.py", "Reasoning/team_reasoning_engine.py"],
            missing=missing,
        ),
    )
    _set_public_surface(answer, natural)
    answer["developer"]["public_team_profile"] = profile.to_dict()
    if assessment is not None:
        answer["developer"]["team_reasoning_assessment"] = assessment.to_dict()
    return answer



def _comparison_natural_language(assessment: Any) -> str:
    return (
        f"Executive Comparison: {assessment.executive_comparison}\n\n"
        f"Strengths: {assessment.strengths.conclusion}\n\n"
        f"Weaknesses: {assessment.weaknesses.conclusion}\n\n"
        f"Historical Comparison: {assessment.historical_comparison.conclusion}\n\n"
        f"Prime Comparison: {assessment.prime_comparison.conclusion}\n\n"
        f"Future Outlook: {assessment.future_outlook.conclusion}\n\n"
        f"Athena Conclusion: {assessment.athena_conclusion}\n\n"
        f"Confidence: {assessment.confidence:.2f}"
    )


def _comparison_observed_facts(assessment: Any) -> List[str]:
    sections = [
        ("Executive comparison", assessment.executive_comparison),
        (assessment.strengths.name, assessment.strengths.conclusion),
        (assessment.weaknesses.name, assessment.weaknesses.conclusion),
        (assessment.historical_comparison.name, assessment.historical_comparison.conclusion),
        (assessment.prime_comparison.name, assessment.prime_comparison.conclusion),
        (assessment.future_outlook.name, assessment.future_outlook.conclusion),
        ("Athena conclusion", assessment.athena_conclusion),
    ]
    return [f"{label}: {body}" for label, body in sections if body]


def player_comparison_answer(ctx, profiles: List[PublicPlayerProfile], question: str) -> Dict[str, object]:
    if len(profiles) < 2:
        return response(
            intent="public_player_comparison_gap",
            title="Comparison needs two known public players",
            engine_conclusion="Athena detected a comparison request but could not resolve two public player profiles yet.",
            observed_facts=[f"Resolved profiles: {len(profiles)}."],
            known_limitations=["Add more public player profiles or clarify the player names."],
            confidence=0.35,
            developer=developer_info("public_player_comparison_gap", getattr(ctx, "files_loaded", []), missing=["second_public_player_profile"]),
        )
    a, b = profiles[0], profiles[1]
    try:
        from Reasoning.comparison_reasoning_engine import ComparisonReasoningEngine
        assessment = ComparisonReasoningEngine().compare_public_players(a, b, question)
    except Exception as ex:  # pragma: no cover - fallback preserves PIF during partial installs
        assessment = None
        reasoning_error = str(ex)
    else:
        reasoning_error = ""

    shared = sorted(set(a.comparison_tags).intersection(b.comparison_tags))
    a_only = sorted(set(a.comparison_tags) - set(b.comparison_tags))[:6]
    b_only = sorted(set(b.comparison_tags) - set(a.comparison_tags))[:6]

    if assessment is not None:
        observed = [
            f"Career identity — {a.display_name}: {a.career_identity}",
            f"Career identity — {b.display_name}: {b.career_identity}",
            f"Style — {a.display_name}: {a.style}.",
            f"Style — {b.display_name}: {b.style}.",
        ] + _comparison_observed_facts(assessment)
        conclusion = assessment.athena_conclusion
        natural = _comparison_natural_language(assessment)
        confidence = assessment.confidence
        known_limitations = list(assessment.limitations)
        intelligence_used = ["public_comparison_guardrail", "comparison_reasoning_engine", "pif_public_comparison_answer"]
        missing = ["official_stats_pack", "playoff_context_pack", "age_curve_model", "live_event_inputs"]
    else:
        observed = [
            f"Career identity — {a.display_name}: {a.career_identity}",
            f"Career identity — {b.display_name}: {b.career_identity}",
            f"Style — {a.display_name}: {a.style}.",
            f"Style — {b.display_name}: {b.style}.",
            f"Shared comparison tags: {', '.join(shared) if shared else 'none seeded yet'}.",
            f"{a.display_name} differentiators: {', '.join(a_only) if a_only else 'seed pending'}.",
            f"{b.display_name} differentiators: {', '.join(b_only) if b_only else 'seed pending'}.",
            "Public comparison route selected; provider-specific owner context is excluded unless explicitly requested.",
        ]
        conclusion = (
            f"This is a public hockey comparison between {a.display_name} and {b.display_name}. "
            f"{a.display_name} is framed around {a.public_value.lower()}, while {b.display_name} is framed around {b.public_value.lower()}."
        )
        natural = (
            f"Public framing: {conclusion}\n\n"
            f"{a.display_name}: {a.career_identity} Style: {a.style}.\n\n"
            f"{b.display_name}: {b.career_identity} Style: {b.style}.\n\n"
            f"Where they overlap: {', '.join(shared) if shared else 'the current seed pack does not identify many overlapping tags yet'}.\n\n"
            f"What separates {a.display_name}: {', '.join(a_only) if a_only else 'seed pending'}.\n"
            f"What separates {b.display_name}: {', '.join(b_only) if b_only else 'seed pending'}.\n\n"
            "Provider-specific league context is excluded from the primary public comparison."
        )
        confidence = 0.78
        known_limitations = [
            "This build uses seeded public identity/career context; full statistical, playoff, and age-curve comparison arrives in later public knowledge packs.",
            "Provider-specific league context is excluded from the main public comparison answer.",
        ]
        intelligence_used = ["public_comparison_guardrail", "pif_public_comparison_answer", "comparison_narrative_seed"]
        missing = ["official_stats_pack", "playoff_context_pack", "age_curve_model", "comparable_player_engine"]
        if reasoning_error:
            missing.append(f"comparison_reasoning_error: {reasoning_error}")

    cards = [
        {"label": a.display_name, "value": a.public_value},
        {"label": b.display_name, "value": b.public_value},
        {"label": "Shared", "value": ", ".join(shared[:3]) if shared else "limited"},
        {"label": "Fantasy", "value": "skipped"},
    ]
    answer = response(
        intent="public_player_comparison",
        title=f"{a.display_name} vs {b.display_name}",
        engine_conclusion=conclusion,
        observed_facts=observed,
        known_limitations=known_limitations,
        confidence=confidence,
        cards=cards,
        developer=developer_info(
            "public_player_comparison",
            getattr(ctx, "files_loaded", []),
            knowledge_used=["public_entity_registry", "public_player_profile_seed", "public_identity_graph"],
            intelligence_used=intelligence_used,
            files_read=["Knowledge/Intelligence/Public/public_player_profiles.py", "Reasoning/comparison_reasoning_engine.py"],
            missing=missing,
        ),
    )
    _set_public_surface(answer, natural)
    answer["developer"]["profiles"] = [p.to_dict() for p in profiles]
    if assessment is not None:
        answer["developer"]["comparison_assessment"] = assessment.to_dict()
    return answer


def team_comparison_answer(ctx, profiles: List[PublicTeamProfile], question: str) -> Dict[str, object]:
    if len(profiles) < 2:
        return response(
            intent="public_team_comparison_gap",
            title="Comparison needs two known public teams",
            engine_conclusion="Athena detected a team comparison but could not resolve two public team profiles yet.",
            observed_facts=[f"Resolved profiles: {len(profiles)}."],
            known_limitations=["Add more public team profiles or clarify the team names."],
            confidence=0.35,
            developer=developer_info("public_team_comparison_gap", getattr(ctx, "files_loaded", []), missing=["second_public_team_profile"]),
        )
    a, b = profiles[0], profiles[1]
    try:
        from Reasoning.comparison_reasoning_engine import ComparisonReasoningEngine
        assessment = ComparisonReasoningEngine().compare_public_teams(a, b, question)
    except Exception as ex:  # pragma: no cover - explicit fallback keeps Scout available
        return response(
            intent="public_team_comparison_gap",
            title=f"{a.display_name} vs {b.display_name}",
            engine_conclusion="Athena detected the team comparison but the comparison engine could not run.",
            observed_facts=[f"Reasoning error: {ex}"],
            known_limitations=["Comparison reasoning engine failed during execution."],
            confidence=0.30,
            developer=developer_info("public_team_comparison_gap", getattr(ctx, "files_loaded", []), missing=["comparison_reasoning_engine"]),
        )

    answer = response(
        intent="public_team_comparison",
        title=f"{a.display_name} vs {b.display_name}",
        engine_conclusion=assessment.athena_conclusion,
        observed_facts=_comparison_observed_facts(assessment),
        known_limitations=list(assessment.limitations),
        confidence=assessment.confidence,
        cards=[
            {"label": a.display_name, "value": a.identity},
            {"label": b.display_name, "value": b.identity},
            {"label": "Comparison", "value": "organizational"},
            {"label": "Fantasy", "value": "skipped"},
        ],
        developer=developer_info(
            "public_team_comparison",
            getattr(ctx, "files_loaded", []),
            knowledge_used=["public_entity_registry", "public_team_profile_seed", "public_identity_graph"],
            intelligence_used=["public_comparison_guardrail", "comparison_reasoning_engine", "pif_public_team_comparison_answer"],
            files_read=["Knowledge/Intelligence/Public/public_team_profiles.py", "Reasoning/comparison_reasoning_engine.py"],
            missing=["live_roster_feed", "salary_cap_feed", "injury_feed", "event_intelligence_feed"],
        ),
    )
    _set_public_surface(answer, _comparison_natural_language(assessment))
    answer["developer"]["profiles"] = [p.to_dict() for p in profiles]
    answer["developer"]["comparison_assessment"] = assessment.to_dict()
    return answer

def _public_gap_message(route: str, question: str, allowed_domains: List[str]) -> str:
    """Return public-facing gap language without exposing implementation details.

    Gap answers are legitimate analyst behavior: Athena should say what it can
    and cannot verify, what evidence would be required, and what it can do next.
    It should not tell a public user about routes, packages, or missing internal
    knowledge packs.
    """
    q = (question or "").strip()
    q_lower = q.lower()

    if route in {"draft_intelligence_gap", "prospect_intelligence_gap"}:
        if any(team in q_lower for team in ["leafs", "maple leafs", "toronto"]):
            return (
                "I can frame Toronto's draft question, but I do not yet have a verified draft-board, pick-order, prospect-ranking, or team-pick feed attached to this path. "
                "For a Leafs draft evaluation, the useful analyst lens is: what picks Toronto actually owns, whether the club is trying to add cost-controlled skill, right-shot defense, center depth, or goaltending depth, and whether any pick is more valuable as a trade asset than as a selection. "
                "Without confirmed pick inventory and prospect evidence, I should not name a specific target or pretend to know their draft board."
            )
        return (
            "I understand this as a draft/prospect question, but I do not yet have enough verified draft intelligence attached to make a confident projection. "
            "A proper answer needs current pick order, prospect rankings, scouting reports, team needs, and recent draft-market movement. "
            "Without that evidence, I can explain the decision factors, but I should not present a first-overall prediction as if it is sourced."
        )

    if route == "event_intelligence_gap":
        return (
            "I recognize this as a recent-event question, but I do not have a verified matching event in the available source set. "
            "I should not substitute unrelated headlines or validation samples. A reliable answer needs dated, source-linked event evidence that matches the team, player, and event type in the question."
        )

    return (
        "I recognize the public sports question, but I do not have enough verified public evidence attached to answer it cleanly yet. "
        "I can still explain what evidence would be required and avoid mixing in fantasy-owner data, rulebook material, or unrelated context."
    )


def _public_gap_title(route: str, fallback: str) -> str:
    if route in {"draft_intelligence_gap", "prospect_intelligence_gap"}:
        return "Draft outlook needs verified evidence"
    if route == "event_intelligence_gap":
        return "No verified matching event yet"
    return fallback if fallback and "knowledge pack" not in fallback.lower() else "More verified public evidence needed"


def gap_answer(ctx, title: str, route: str, question: str, allowed_domains: List[str], blocked_domains: List[str]) -> Dict[str, object]:
    public_text = _public_gap_message(route, question, allowed_domains)
    return response(
        intent=route,
        title=_public_gap_title(route, title),
        engine_conclusion=public_text,
        observed_facts=[
            f"Question asked: {question}",
            "Athena did not find enough verified public evidence to answer this as a sourced analysis.",
            "Fantasy-owner data, rulebook material, and unrelated public context were intentionally excluded.",
        ],
        known_limitations=[
            "Verified draft/prospect/current-event feeds are not yet fully attached to this answer path.",
            "This answer is intentionally conservative rather than speculative.",
        ],
        confidence=0.64,
        cards=[],
        natural_language_response=public_text,
        developer=developer_info(
            route,
            getattr(ctx, "files_loaded", []),
            knowledge_used=["pif_intent_router", "public_domain_guardrails"],
            intelligence_used=["public_gap_composition", "pif_gap_guardrail"],
            files_read=["Knowledge/Intelligence/Routing/request_router.py", "Knowledge/Intelligence/Public/public_answers.py"],
            missing=allowed_domains,
        ),
    )
