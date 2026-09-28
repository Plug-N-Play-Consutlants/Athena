"""Public-facing answer helpers for PIF-1.

Drop 4e37 reconnects public identity routing to Athena's deeper reasoning
pipeline. Seed profiles remain the identity substrate; they are no longer the
final answer when richer player intelligence is available.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from Knowledge.Intelligence.Entities.entity_registry import PublicEntity
from Knowledge.Intelligence.Public.public_player_profiles import PublicPlayerProfile, profile_for_entity
from Knowledge.Intelligence.Public.public_team_profiles import PublicTeamProfile, profile_for_team_entity
from Scout.conversation.responses import developer_info, response
from Experience.renderer import attach_experience_contract
from Knowledge.Intelligence.Public.player_evidence import player_evidence, player_tier, authoritative_statistical_view
from Athena.player_assessment import assess_player, assessment_copy
from Knowledge.Intelligence.Entities.entity_registry import find_by_id




def _player_experience_seed(profile: PublicPlayerProfile) -> Dict[str, object]:
    seed: Dict[str, object] = {}
    entity = find_by_id(profile.entity_id)
    evidence = player_evidence(profile.display_name, team=profile.team, position=profile.position,
                               birth_date=entity.birth_date if entity else "")
    if evidence:
        seed.update(evidence)
    return seed


def _player_payload(profile: PublicPlayerProfile, seed: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    seed = _player_experience_seed(profile) if seed is None else seed
    entity = find_by_id(profile.entity_id)
    age = seed.get("age")
    if age is None and entity and entity.birth_date:
        try:
            birth = date.fromisoformat(entity.birth_date)
            today = date.today()
            age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        except ValueError:
            pass
    return {
        "full_name": profile.display_name,
        "name": profile.display_name,
        "jersey_number": str(seed.get("jersey_number") or ""),
        "team": profile.team,
        "position": profile.position,
        "photo_url": str(seed.get("photo_url") or ""),
        "status": "",
        "draft": profile.draft,
        "height": profile.physical_profile.split(" center", 1)[0] if profile.physical_profile and "foot" in profile.physical_profile else "",
        "nationality": profile.nationality,
        "role": profile.role,
        "age": age if age is not None else "",
    }


def _entity_label(entity: PublicEntity) -> str:
    label = entity.metadata.get("disambiguation_label") if isinstance(entity.metadata, dict) else None
    return str(label or f"{entity.canonical_name} — {entity.position or entity.entity_type} — {entity.team or entity.league}")


def _entity_prompt(entity: PublicEntity) -> str:
    team = entity.team or ""
    if entity.entity_id == "nhl.player.sebastian_aho_car":
        return "Sebastian Aho Carolina Hurricanes center"
    if entity.entity_id == "nhl.player.sebastian_aho_swe":
        return "Sebastian Aho Swedish defenseman"
    return "Tell me about " + " ".join(part for part in [entity.canonical_name, team] if part).strip()


def _profile_matches_public_entity(evaluation: Dict[str, Any], profile: PublicPlayerProfile) -> bool:
    """Prevent seeded public disambiguation from merging two same-name players."""
    player = evaluation.get("player") if isinstance(evaluation.get("player"), dict) else {}
    eval_team = str(player.get("nhl_team") or "").upper()
    public_team = (profile.team or "").upper()
    from Knowledge.Intelligence.Entities.entity_registry import entities_by_type
    if sum(entity.canonical_name.casefold() == profile.display_name.casefold() for entity in entities_by_type("player")) > 1:
        # A name-only local row cannot establish which same-name person it is.
        if str(player.get("public_entity_id") or player.get("entity_id") or "") != profile.entity_id:
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
            return None, None, None
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
    answer["display_contract"] = "athena_response"
    return attach_experience_contract(answer)


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



def _public_limitations(items: List[Any]) -> List[str]:
    public: List[str] = []
    replacements = {
        "Player Intelligence 4B.1 does not yet evaluate line deployment, power-play role, injuries, schedule strength, or future projection curves.": "Line deployment, power-play role, injury context, schedule strength, and projection curves are not fully attached to this player view yet.",
        "PIF Build 004 does not yet ingest live injuries, teammate deployment, or current official game logs automatically.": "Live injuries, teammate deployment, and official game-log feeds are not fully attached to this answer path yet.",
    }
    for item in items:
        text = str(item or "").strip()
        if not text:
            continue
        text = replacements.get(text, text)
        text = re.sub(r"\b(Player Intelligence|PIF Build|Build \d+|drop\w+)\b[^.]*", "", text).strip(" .")
        if text and text not in public:
            public.append(text)
    return public



def _ordinal_pick(value: str) -> str:
    try:
        n = int(str(value).strip())
    except (TypeError, ValueError):
        return str(value).strip()
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


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
        draft_text = profile.draft
        match = re.match(r"(\d{4}) NHL Draft, (\d+)(?:st|nd|rd|th)? overall, (.+)", draft_text)
        if match:
            year, pick, team = match.groups()
            draft_text = f"the {_ordinal_pick(pick)} overall pick in the {year} NHL Draft by {team}"
        else:
            draft_text = "the " + draft_text
        opening = f"{profile.display_name} entered the NHL as {draft_text} and has developed into {profile.role}."

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
        clean_style = style.rstrip(".").strip()
        if clean_style and clean_style[0].islower():
            clean_style = clean_style[0].upper() + clean_style[1:]
        paragraphs.append(clean_style + ".")

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
        paragraphs.append(f"Analytical lens: {profile.analytical_read}")
    elif profile.organizational_context:
        paragraphs.append("Analytical lens: " + profile.organizational_context)

    roster_read_parts: List[str] = []
    if profile.roster_context:
        roster_read_parts.append(profile.roster_context)
    limitation = next((item for item in profile.known_limitations if item), "")
    if limitation:
        roster_read_parts.append("Sharper live team analysis still needs: " + limitation)
    if roster_read_parts:
        paragraphs.append("Roster read: " + " ".join(part.strip() for part in roster_read_parts if part and part.strip()))

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
        return "Sebastian Aho — C / CAR"
    if entity.entity_id == "nhl.player.sebastian_aho_swe":
        return "Sebastian Aho — D / Sweden"
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
            # Entity selection resolves the subject of the pending inquiry; it
            # must not silently replace that inquiry with a profile request.
            "continuation": {
                "origin_intent": "public_entity_disambiguation",
                "subject_entity_id": entity.entity_id,
                "pending_question": question,
            },
        })

    natural = (
        "There is more than one public sports profile matching that name. "
        "Here are the candidates I found; choose one to continue with the correct player.\n\n"
        + "\n".join(f"• {fact}" for fact in facts)
    )
    answer = response(
        intent="public_entity_disambiguation",
        title="Which Sebastian Aho?" if "sebastian aho" in question.lower() else "Which player did you mean?",
        engine_conclusion="More than one public sports entity matches that name, so the identity must be selected before player-specific reasoning.",
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


def _current_player_evidence(lifecycle: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract evidence-backed current-player signals without converting categories into facts."""
    recent = (lifecycle or {}).get("recent_news") if isinstance(lifecycle, dict) else []
    items: List[Dict[str, str]] = []
    corpus: List[str] = []
    for item in recent or []:
        if not isinstance(item, dict):
            continue
        summary = str(item.get("summary") or "").strip()
        meta = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        story = meta.get("story") if isinstance(meta.get("story"), dict) else {}
        title = str(story.get("title") or summary).strip()
        publisher = str(meta.get("publisher") or story.get("source_display_name") or "").strip()
        if not title:
            continue
        lower = f"{title} {summary}".lower()
        # Section-aware evidence priority for current player assessment. Performance,
        # camp/preseason, deployment and roster signals should outrank merely related
        # contract/business/debut coverage when no NHL statistical sample exists.
        performance_terms = (
            "camp", "training camp", "preseason", "pre-season", "poise", "performance",
            "impressed", "standout", "skated", "line", "linemate", "deployment", "role",
            "roster", "opening night", "made the team", "earned a roster spot", "coach",
        )
        related_penalties = ("bonus", "payment", "salary", "contract", "cap hit")
        relevance = sum(2 for token in performance_terms if token in lower) - sum(1 for token in related_penalties if token in lower)
        items.append({"title": title, "summary": summary, "publisher": publisher, "assessment_relevance": relevance})
        corpus.extend([title.lower(), summary.lower()])
    items.sort(key=lambda item: int(item.get("assessment_relevance") or 0), reverse=True)
    text = " ".join(corpus)
    return {
        "items": items,
        "text": text,
        "camp": any(token in text for token in ("camp", "training camp")),
        "preseason": any(token in text for token in ("preseason", "pre-season")),
        "roster": any(token in text for token in ("roster", "opening night", "made the team", "earned a roster spot")),
        "rookie": any(token in text for token in ("rookie", "debut", "first nhl")),
    }


def _player_followup_prompts(name: str, *, team: str = "", lifecycle: Optional[Dict[str, Any]] = None, established: bool = False, early_career: bool = False) -> List[str]:
    """Derive next investigations from evidence and lifecycle, with career-stage-aware wording."""
    prompts: List[str] = []
    current = _current_player_evidence(lifecycle)
    if current["camp"] or current["preseason"]:
        if established:
            prompts.append(f"What has {name} shown in camp and preseason, and does it change the outlook for his early-season form or deployment?")
        elif early_career:
            prompts.append(f"What has {name} shown in camp and preseason, and what does it suggest about his initial NHL role?")
        else:
            prompts.append(f"What do verified camp and preseason reports reveal about {name}'s current role?")
    if established:
        prompts.append(f"How does {name}'s current production compare with his recent career baseline?")
    elif early_career:
        prompts.append(f"What does {name}'s developmental track suggest about his NHL transition?")
    else:
        prompts.append(f"What verified professional history and current deployment evidence are available for {name}?")
    if team:
        prompts.append(f"How does {name} fit into {team}'s current roster and organizational plans?")
    prompts.append(f"What are the biggest evidence-backed uncertainties in {name}'s outlook?")
    return list(dict.fromkeys(prompts))[:4]


def _lifecycle_transition_assessment(name: str, lifecycle: Dict[str, Any]) -> Dict[str, str]:
    """Compose bounded early-career analysis from the actual current evidence discovered."""
    current = _current_player_evidence(lifecycle)
    items = current["items"]
    state = str(lifecycle.get("lifecycle_state") or "")
    team = str(lifecycle.get("team") or "")
    if not items and state != "nhl_roster_player":
        return {}

    evidence_bits: List[str] = []
    if current["camp"]:
        evidence_bits.append("camp")
    if current["preseason"]:
        evidence_bits.append("preseason")
    if current["roster"] or state == "nhl_roster_player":
        evidence_bits.append("roster")
    if current["rookie"]:
        evidence_bits.append("rookie/debut")
    evidence_bits = list(dict.fromkeys(evidence_bits))
    evidence_label = ", ".join(evidence_bits) if evidence_bits else "current professional"

    headlines = [item["title"] for item in items[:2] if item.get("title")]
    detail = (" Current reporting includes “" + "” and “".join(headlines) + "”.") if headlines else ""
    current_season = (
        f"With no meaningful NHL regular-season sample yet, {name}'s current read comes from {evidence_label} evidence rather than an empty statistical line."
        + detail
    )
    if team and state == "nhl_roster_player":
        current_season += f" The reconciled evidence places him on {team}'s NHL roster, so the immediate evaluation is his transition into regular-season deployment and production."

    trajectory = (
        f"{name}'s trajectory is developmental rather than NHL-statistical at this stage. Draft and development history should carry more weight until a meaningful NHL sample exists, while current professional evidence establishes the next stage of that progression."
    )
    outlook = (
        "The near-term outlook is an NHL-transition projection: use verified camp/preseason and roster evidence to establish the opportunity, then test it against regular-season deployment, role stability, and production as those observations arrive."
    )
    return {"current_season": current_season, "career_trend": trajectory, "future_outlook": outlook}

def player_profile_answer(ctx, profile: PublicPlayerProfile, question: str) -> Dict[str, object]:
    brief, evaluation, assessment = _build_reasoned_player_brief(profile, question)
    lifecycle = None
    from Knowledge.Intelligence.Entities.entity_registry import entities_by_type
    same_name_count = sum(entity.canonical_name.casefold() == profile.display_name.casefold() for entity in entities_by_type("player"))
    if same_name_count == 1:
        try:
            from Knowledge.Intelligence.Public.player_lifecycle import resolve_player_lifecycle
            lifecycle = resolve_player_lifecycle(profile.display_name, allow_network=True)
            if not isinstance(lifecycle, dict) or lifecycle.get("status") != "available":
                lifecycle = None
        except Exception:
            lifecycle = None

    observed = [
        f"Identity: {profile.display_name} is a {profile.position} for {profile.team}.",
        f"Public role: {profile.role}.",
        f"Style: {profile.style}.",
        f"Draft context: {profile.draft or 'not seeded yet'}.",
    ]
    observed.extend(profile.career_notes[:5])
    if lifecycle:
        for item in (lifecycle.get("recent_news") or [])[:3]:
            if isinstance(item, dict) and item.get("summary"):
                observed.append("Current professional context: " + str(item.get("summary")))
    if profile.awards:
        observed.append("Awards/legacy signals: " + ", ".join(profile.awards) + ".")

    seed = _player_experience_seed(profile)
    player_payload = _player_payload(profile, seed)
    seeded_stats = seed.get("stats") if isinstance(seed.get("stats"), dict) else {}
    cards = [
        {"label": "Player", "value": profile.display_name},
        {"label": "Number", "value": player_payload.get("jersey_number", "")},
        {"label": "Team", "value": profile.team},
        {"label": "Position", "value": profile.position},
        {"label": "Public value", "value": profile.public_value},
    ]
    for label, key in [("Goals", "goals"), ("Assists", "assists"), ("Points", "points"), ("P/GP", "ppg"), ("+/-", "+/-")]:
        value = seeded_stats.get(key) if isinstance(seeded_stats, dict) else ""
        if value is not None and value != "":
            cards.append({"label": label, "value": str(value)})

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
        known_limits = _public_limitations(list((evaluation or {}).get("limitations") or []) if isinstance(evaluation, dict) else [])
        known_limits.extend(_public_limitations(profile.known_limitations))
    else:
        title = f"{profile.display_name} — {profile.position} / {profile.team}"
        confidence = 0.80
        conclusion = profile.career_identity
        natural = _compose_public_player_copy(profile, question, fallback=conclusion, evaluation=evaluation)
        intelligence_used = ["pif_public_profile_answer", "seed_profile_fallback"]
        missing = ["local_player_reasoning_match"]
        known_limits = _public_limitations(list(profile.known_limitations)) + ["Verified NHL career and season evidence is unavailable for this resolved identity; current rating and career legacy remain unassigned."]

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
    answer["player"] = player_payload
    answer["jersey_number"] = player_payload.get("jersey_number", "")
    answer["photo_url"] = player_payload.get("photo_url", "")
    answer["stats"] = seeded_stats
    answer["season_statistics"] = seed.get("season_statistics") if isinstance(seed.get("season_statistics"), list) else []
    if seed.get("source") == "nhl_player_landing":
        professional = assess_player(seed)
        answer["professional_assessment"] = professional
        answer["player_tier"] = professional["current_tier"]
        answer["career_legacy"] = professional["career_legacy"]
        answer["career_stage"] = professional["career_stage"]
        answer["player_evidence_season"] = professional["as_of_season"]
        answer["player_career_games"] = seed.get("career_games")
        answer["season_statistics"] = [
            {"season": item["season"], "team": seed.get("team"), "gp": item["gp"],
             "g": item["goals"], "a": item["assists"], "pts": item["points"],
             "ppg": round(item["points"] / item["gp"], 3) if item.get("gp") and isinstance(item.get("points"), (int, float)) else "",
             "plus_minus": item["plus_minus"]}
            for item in seed.get("season_history", []) if item.get("season") in professional["window_seasons"]
        ]
        natural = assessment_copy(profile.display_name, seed, professional)
        answer["engine_conclusion"] = natural.split("\n\n", 1)[0]
        answer["observed_facts"] = [
            f"NHL landing identity: {profile.display_name}, NHL ID {seed['nhl_id']}, birth date {seed['birth_date']}.",
            f"Last three available NHL regular seasons: {professional['recent_points']} points in {professional['recent_games']} games over {professional['seasons_used']} seasons.",
            f"NHL career: {seed.get('career_points')} points in {seed.get('career_games')} games.",
        ]
        answer["confidence"] = 0.85 if professional["seasons_used"] >= 3 else 0.7
        answer["known_limitations"] = list(dict.fromkeys(professional["limitations"] + _public_limitations(profile.known_limitations)))
        answer["assessment_badges"] = professional["rookie_tags"]
        answer["cards"] = [card for card in answer.get("cards", [])
                           if str(card.get("label") or "").strip().lower() not in
                           {"role", "asset tier", "career tier", "public value", "prime window"}]
        answer["developer"].setdefault("knowledge_used", []).append("nhl_player_landing")
        answer["developer"]["assessment_window"] = professional
        answer["title"] = f"{profile.display_name} — {profile.position} / {seed.get('team') or profile.team}"
    else:
        answer["assessment_badges"] = ["Assessment Pending"]
        answer["confidence"] = min(float(answer.get("confidence") or .5), .65)
        answer["title"] = f"{profile.display_name} — {profile.position} / {profile.nationality or 'team unverified'}"
        answer["player"]["team"] = ""
        answer["cards"] = [card for card in answer.get("cards", []) if card.get("label", "").lower() in {"player", "position"}]
        natural = (
            f"Athena resolved {profile.display_name}'s identity ({profile.position}, {profile.nationality or 'nationality unverified'}) "
            "but does not have a matched NHL career and season record for this player. "
            "The current club, statistical snapshot, current tier, and career legacy remain unverified. "
            "Historical profile notes are retained as leads for further evidence, not as a current player assessment."
        )
        answer["engine_conclusion"] = natural
        answer["observed_facts"] = [f"Identity: {profile.display_name}, {profile.position}, {profile.nationality}."]
    answer = _set_public_surface(answer, natural)
    answer["developer"]["public_player_profile"] = profile.to_dict()
    answer["developer"]["player_experience_seed"] = seed
    if isinstance(evaluation, dict):
        answer["developer"]["player_evaluation"] = evaluation
    if assessment is not None:
        answer["developer"]["reasoning_assessment"] = assessment.as_dict() if hasattr(assessment, "as_dict") else str(assessment)
    if brief:
        answer["developer"]["executive_brief"] = brief
    if lifecycle:
        answer["developer"]["player_lifecycle"] = lifecycle
        answer["developer"].setdefault("knowledge_used", []).append("player_lifecycle")
        if lifecycle.get("recent_news"):
            answer["developer"].setdefault("knowledge_used", []).append("current_news")
    answer["suggested_prompts"] = _player_followup_prompts(
        profile.display_name, team=profile.team, lifecycle=lifecycle,
        established=bool(seed.get("career_games")), early_career=bool(seed.get("career_games") and seed.get("career_games") < 40)
    )
    return attach_experience_contract(answer)


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



def _comparison_public_copy(value: Any) -> str:
    text = str(value or "").strip()
    replacements = {
        "Athena compares": "The comparison turns on",
        "In this build, Athena can compare": "Current evidence supports comparing",
        "is seeded as ": "is best represented as ",
        "are seeded as ": "are best represented as ",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def _comparison_natural_language(assessment: Any) -> str:
    return (
        f"Overall: {_comparison_public_copy(assessment.executive_comparison)}\n\n"
        f"Strengths: {_comparison_public_copy(assessment.strengths.conclusion)}\n\n"
        f"Limitations: {_comparison_public_copy(assessment.weaknesses.conclusion)}\n\n"
        f"Career context: {_comparison_public_copy(assessment.historical_comparison.conclusion)}\n\n"
        f"At their peaks: {_comparison_public_copy(assessment.prime_comparison.conclusion)}\n\n"
        f"Outlook: {_comparison_public_copy(assessment.future_outlook.conclusion)}\n\n"
        f"Bottom line: {_comparison_public_copy(assessment.athena_conclusion)}\n\n"
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
    public_labels = {"Athena conclusion": "Bottom line", "Historical Comparison": "Career context", "Prime Comparison": "At their peaks", "Future Outlook": "Outlook"}
    return [f"{public_labels.get(label, label)}: {_comparison_public_copy(body)}" for label, body in sections if body]


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

    request_bundle = getattr(ctx, "request_evidence", {}) if ctx is not None else {}
    supplied_players = request_bundle.get("players", []) if isinstance(request_bundle, dict) else []
    official_by_name = {}
    for supplied in supplied_players if isinstance(supplied_players, list) else []:
        if not isinstance(supplied, dict):
            continue
        subject = supplied.get("subject") or {}
        official = supplied.get("official_player_record") or {}
        if subject.get("name") and isinstance(official, dict) and official:
            official_by_name[str(subject["name"]).casefold()] = official

    recent_lines = []
    recent_rows = {}
    recent_series = {}
    for profile in (a, b):
        official = official_by_name.get(profile.display_name.casefold(), {})
        authoritative = authoritative_statistical_view(official, window_size=3) if official else {}
        rows = authoritative.get("recent_window", []) if isinstance(authoritative, dict) else []
        if rows:
            recent_series[profile.display_name] = rows
            row = rows[0]
            recent_rows[profile.display_name] = row
            rate = row["points"] / row["gp"]
            recent_lines.append(f"Official NHL record — {profile.display_name}: {row.get('season')} — {row['points']} points in {row['gp']} games ({rate:.2f} points/game).")
            if len(rows) > 1:
                window = rows[:3]
                games = sum(r["gp"] for r in window)
                points = sum(r["points"] for r in window)
                recent_lines.append(f"Verified recent window — {profile.display_name}: {points} points in {games} games across {len(window)} NHL seasons ({points/games:.2f} points/game).")

    if assessment is not None:
        assessment_facts = _comparison_observed_facts(assessment)
        if recent_lines:
            assessment_facts = [fact for fact in assessment_facts if not (
                str(fact).startswith("Relative Weaknesses:") and "official current-season stats" in str(fact).casefold()
            )]
        observed = [
            f"Career identity — {a.display_name}: {a.career_identity}",
            f"Career identity — {b.display_name}: {b.career_identity}",
            f"Style — {a.display_name}: {a.style}.",
            f"Style — {b.display_name}: {b.style}.",
        ] + recent_lines + assessment_facts
        conclusion = assessment.athena_conclusion
        natural = _comparison_natural_language(assessment)
        if len(recent_rows) == 2:
            ar, br = recent_rows[a.display_name], recent_rows[b.display_name]
            def _window_text(name):
                rows = recent_series.get(name, [])
                games = sum(r["gp"] for r in rows)
                points = sum(r["points"] for r in rows)
                seasons = ", ".join(str(r.get("season") or "") for r in rows)
                return f"{points} points in {games} games across {len(rows)} verified season(s) ({seasons})"
            a_rows = recent_series[a.display_name]
            b_rows = recent_series[b.display_name]
            a_games = sum(r["gp"] for r in a_rows); a_points = sum(r["points"] for r in a_rows)
            b_games = sum(r["gp"] for r in b_rows); b_points = sum(r["points"] for r in b_rows)
            a_rate = a_points / a_games; b_rate = b_points / b_games
            a_latest = ar["points"] / ar["gp"]; b_latest = br["points"] / br["gp"]
            if abs(a_rate - b_rate) < 0.01:
                statistical_read = f"Their verified three-season scoring rates are effectively even ({a_rate:.2f} vs {b_rate:.2f} points/game)."
            else:
                leader, leader_rate, other_rate = (a.display_name, a_rate, b_rate) if a_rate > b_rate else (b.display_name, b_rate, a_rate)
                statistical_read = f"{leader} holds the higher verified three-season scoring rate ({leader_rate:.2f} vs {other_rate:.2f} points/game)."
            natural = (
                f"Verified NHL statistical comparison: {a.display_name} has {_window_text(a.display_name)}; "
                f"{b.display_name} has {_window_text(b.display_name)}. {statistical_read} "
                f"In the latest verified season, {a.display_name} produced {a_latest:.2f} points/game and "
                f"{b.display_name} produced {b_latest:.2f}.\n\n"
                "Context beyond scoring: " + natural
            )
            natural = natural.replace("live injuries, current deployment, official current-season stats and age-curve feeds are not attached yet", "live injuries, current deployment and age-curve evidence are not fully attached yet")
        confidence = max(assessment.confidence, 0.86 if len(recent_rows) == 2 else assessment.confidence)
        known_limitations = _public_limitations(list(assessment.limitations))
        if len(recent_rows) == 2:
            known_limitations = [item for item in known_limitations if "official current-season stats" not in item.casefold() and "official stats" not in item.casefold()]
        intelligence_used = ["public_comparison_guardrail", "comparison_reasoning_engine", "athena_request_evidence_bundle", "pif_public_comparison_answer"]
        missing = ["playoff_context_pack", "age_curve_model", "live_event_inputs"]
        if len(recent_rows) < 2:
            missing.append("official_stats_pack")
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
            knowledge_used=["public_entity_registry", "public_identity_graph"] + (["official_nhl_player_record"] if recent_lines else ["public_player_profile_seed"]),
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


def lifecycle_player_answer(ctx, lifecycle: Dict[str, Any], question: str) -> Dict[str, object]:
    """Compose an adaptive public player surface from reconciled lifecycle evidence."""
    name = str(lifecycle.get("name") or question or "Player")
    team = str(lifecycle.get("team") or "")
    position = str(lifecycle.get("position") or "")
    state = str(lifecycle.get("lifecycle_state") or "prospect")
    draft = str(lifecycle.get("draft") or "")
    recent_news = lifecycle.get("recent_news") if isinstance(lifecycle.get("recent_news"), list) else []
    developmental = lifecycle.get("developmental_evidence") if isinstance(lifecycle.get("developmental_evidence"), list) else []

    state_label = {
        "nhl_roster_player": "NHL roster player",
        "professional_player": "professional player",
        "organizational_prospect": "organizational prospect",
        "drafted": "drafted prospect",
        "draft_eligible": "draft-eligible prospect",
        "prospect": "prospect",
    }.get(state, state.replace("_", " "))
    title_bits = [name]
    if position:
        title_bits.append(position)
    if team and team not in {"N/A", "(N/A)", "FA"}:
        title_bits.append(team)
    title = " — ".join(title_bits)

    cards: List[Dict[str, Any]] = [{"label": "Lifecycle", "value": state_label.title()}]
    if team and team not in {"N/A", "(N/A)", "FA"}:
        cards.append({"label": "Current team", "value": team})
    if position:
        cards.append({"label": "Position", "value": position})
    if draft:
        cards.append({"label": "Draft", "value": draft})
    def meaningful_games(item):
        if not isinstance(item, dict):
            return False
        try:
            return float((item.get("metadata") or {}).get("GP") or 0) >= 40
        except (TypeError, ValueError):
            return False
    established = state in {"nhl_roster_player", "established_nhl_player"} and any(map(meaningful_games, developmental))
    transition = {} if established else _lifecycle_transition_assessment(name, lifecycle)
    if transition.get("current_season"):
        cards.append({"label": "Current Season", "value": transition["current_season"]})
    if transition.get("career_trend"):
        cards.append({"label": "Career Trend", "value": transition["career_trend"]})
    if transition.get("future_outlook"):
        cards.append({"label": "Future Outlook", "value": transition["future_outlook"]})

    paragraphs: List[str] = []
    if team and team not in {"N/A", "(N/A)", "FA"}:
        if established:
            paragraphs.append(f"{name} is an established NHL player associated with {team}. The attached evidence does not yet establish a complete current professional player card.")
        else:
            paragraphs.append(f"{name} is currently resolved as a {state_label} with {team}. Athena is treating that current organizational identity as newer context while retaining earlier prospect/development observations as historical evidence.")
    else:
        paragraphs.append(f"{name} is currently resolved as a {state_label}. Athena has identity/development evidence for the player, but the attached evidence does not yet establish a newer professional-team affiliation strongly enough to overwrite that state.")
    if draft:
        paragraphs.append(f"Draft context: {draft}.")
    if transition.get("current_season"):
        paragraphs.append(transition["current_season"])
    if recent_news:
        headlines = [str(item.get("summary") or "").strip() for item in recent_news[:3] if isinstance(item, dict) and str(item.get("summary") or "").strip()]
        if headlines:
            paragraphs.append("Recent evidence includes: " + "; ".join(headlines) + ".")
    if developmental and not established:
        paragraphs.append("Athena also retains developmental/provider observations for this player rather than discarding them when the lifecycle advances.")
    if established:
        paragraphs.append("Career and current-season NHL evidence should establish his present role and contribution; missing professional statistics are not inferred.")
    else:
        paragraphs.append("The player view should expand as verified junior, college, minor-league, NHL production, scouting, deployment, and current-news evidence becomes available; missing statistics are not inferred.")
    natural = "\n\n".join(paragraphs)

    observed: List[str] = []
    for item in lifecycle.get("evidence") or []:
        if not isinstance(item, dict):
            continue
        summary = str(item.get("summary") or "").strip()
        source = str(item.get("source") or "evidence")
        if summary:
            observed.append(f"{source}: {summary}")
        if len(observed) >= 6:
            break

    answer = response(
        intent="public_player_profile",
        title=title,
        engine_conclusion=paragraphs[0],
        observed_facts=observed,
        known_limitations=list(lifecycle.get("limitations") or []),
        confidence=0.82 if team and recent_news else 0.68,
        cards=cards,
        developer=developer_info(
            "public_player_lifecycle",
            getattr(ctx, "files_loaded", []),
            knowledge_used=["player_identity", "player_lifecycle", "current_news", "developmental_evidence"],
            intelligence_used=["player_lifecycle_reconciliation", "adaptive_player_composition"],
            files_read=["Knowledge/Intelligence/Public/player_lifecycle.py", "Output/player_master.json", "Raw/Fantrax-Players-JHLPAA.csv"],
            missing=[] if recent_news else ["current_professional_evidence"],
        ),
    )
    answer["player"] = {
        "full_name": name, "name": name, "team": team, "position": position,
        "draft": draft, "status": state_label, "photo_url": "", "jersey_number": "",
    }
    for item in developmental:
        meta = item.get("metadata") if isinstance(item, dict) and isinstance(item.get("metadata"), dict) else {}
        age = meta.get("Age") or meta.get("age")
        if str(age).isdigit():
            answer["player"]["age"] = age
            break
    if established:
        answer["assessment_badges"] = ["Current Rating Pending", "Veteran"] if any(
            isinstance(item, dict) and str((item.get("metadata") or {}).get("Age") or "").isdigit()
            and int((item.get("metadata") or {}).get("Age")) >= 30 for item in developmental
        ) else ["Current Rating Pending", "NHL Roster Player"]
        if any(isinstance(item, dict) and "named" in str(item.get("summary") or "").casefold()
               and "captain" in str(item.get("summary") or "").casefold()
               and "nhl.com" in str((item.get("metadata") or {}).get("publisher") or "").casefold()
               for item in recent_news):
            answer["assessment_badges"].append("Core Asset")
    elif state == "nhl_roster_player":
        answer["assessment_badges"] = ["NHL Roster Player"]
    elif state in {"organizational_prospect", "drafted", "draft_eligible", "prospect"}:
        answer["assessment_badges"] = ["Prospect"]
    relevant_stats: Dict[str, Any] = {}
    season_statistics: List[Dict[str, Any]] = []
    for item in developmental:
        if not isinstance(item, dict):
            continue
        if item.get("source") == "fantrax_player_export":
            continue  # Fantasy scoring snapshots are not official NHL statistics.
        meta = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        try:
            gp = int(float(meta.get("GP") or meta.get("games_played") or 0))
        except (TypeError, ValueError):
            gp = 0
        if gp <= 0:
            continue
        points = meta.get("Pt") if meta.get("Pt") not in (None, "") else meta.get("points")
        relevant_stats = {"games_played": gp}
        if points not in (None, ""):
            relevant_stats["points"] = points
        season_statistics.append({"source": item.get("source"), "gp": gp, "points": points})
        break
    answer["stats"] = relevant_stats
    answer["season_statistics"] = season_statistics
    official = player_evidence(name, team=team, position=position)
    if official:
        answer["player"].update({key: official.get(key) for key in ("age", "jersey_number", "photo_url") if official.get(key) is not None})
        answer["player"]["team"] = official.get("team") or team
        answer["stats"] = official.get("stats") or {}
        professional = assess_player(official)
        answer["season_statistics"] = [
            {"season": item["season"], "team": official.get("team"), "gp": item["gp"],
             "g": item["goals"], "a": item["assists"], "pts": item["points"],
             "ppg": round(item["points"] / item["gp"], 3) if item.get("gp") and isinstance(item.get("points"), (int, float)) else "",
             "plus_minus": item["plus_minus"]}
            for item in (official.get("statistical_evidence", {}).get("season_series", official.get("season_history", []))) if item.get("season") in professional["window_seasons"]
        ]
        answer["professional_assessment"] = professional
        answer["player_tier"] = professional["current_tier"]
        answer["career_legacy"] = professional["career_legacy"]
        answer["career_stage"] = professional["career_stage"]
        answer["player_career_games"] = official.get("career_games")
        answer["player_evidence_season"] = professional["as_of_season"]
        answer["assessment_badges"] = professional["rookie_tags"]
        answer["cards"] = [card for card in cards if card.get("label") not in {"Current Season", "Career Trend", "Future Outlook"}]
        natural = assessment_copy(name, official, professional)
        answer["engine_conclusion"] = natural.split("\n\n", 1)[0]
        answer["known_limitations"] = professional["limitations"]
        answer["developer"].setdefault("knowledge_used", []).append("nhl_player_landing")
        answer["developer"]["assessment_window"] = professional
    answer = _set_public_surface(answer, natural)
    answer["developer"]["player_lifecycle"] = lifecycle
    established = established or bool(official and (official.get("career_games") or 0) >= 40)
    answer["suggested_prompts"] = _player_followup_prompts(name, team=team, lifecycle=lifecycle,
                                                            established=established, early_career=not established)
    return attach_experience_contract(answer)
