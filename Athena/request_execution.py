"""Athena's question execution boundary for Scout and future experiences."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable

from Core.version import ATHENA_VERSION


@dataclass(frozen=True)
class AthenaRequest:
    question: str
    mode: str = "fantasy"
    context: Any = None
    sections: Iterable[str] = ()
    continuation: Any = None


def _continued_question(question: str, mode: str, continuation: Any) -> tuple[str, str]:
    """Use an advisory subject hint; specialists still acquire their own evidence."""
    if mode != "public" or not isinstance(continuation, dict):
        return question, "none"
    origin = continuation.get("origin_intent")
    if origin not in {"live_event_intelligence", "public_player_profile", "public_entity_disambiguation"}:
        return question, "ignored"
    from Knowledge.Intelligence.Entities.entity_registry import find_by_id, searchable_names
    import re
    entity = find_by_id(str(continuation.get("subject_entity_id") or ""))
    expected_type = "team" if origin == "live_event_intelligence" else "player"
    if entity is None or entity.entity_type != expected_type:
        return question, "ignored"
    if origin == "public_entity_disambiguation":
        pending = str(continuation.get("pending_question") or "").strip()
        if not pending:
            return question, "ignored"
        position = {"D": "defenseman", "C": "center", "G": "goaltender", "LW": "left winger", "RW": "right winger"}.get(entity.position, entity.position)
        nationality = {"Sweden": "Swedish", "Finland": "Finnish", "Canada": "Canadian", "United States": "American"}.get(entity.nationality, entity.nationality)
        return f"{pending.rstrip(' ?')} concerning {nationality} {position} {entity.canonical_name}?", "resolved_pending_inquiry"
    if origin == "public_player_profile":
        from Knowledge.Intelligence.Entities.entity_registry import entities_by_type
        from Knowledge.Intelligence.Entities.entity_extractor import resolve_qualified_player
        explicitly_qualified = resolve_qualified_player(question)
        if explicitly_qualified is not None and explicitly_qualified.status in {"qualified_resolved", "qualification_unresolved"}:
            return question, "explicit_subject"
        other = [player for player in entities_by_type("player") if player.canonical_name.casefold() != entity.canonical_name.casefold() and re.search(r"(?<!\w)" + re.escape(player.canonical_name) + r"(?!\w)", question, re.I)]
        if other:
            return question, "explicit_subject"
        if not re.search(r"(?<!\w)" + re.escape(entity.canonical_name) + r"(?!\w)", question, re.I) and not re.search(r"\b(he|she|they|his|her|their|this player)\b", question, re.I):
            return question, "ignored"
        position = {"D": "defenseman", "C": "center", "G": "goaltender", "LW": "left winger", "RW": "right winger"}.get(entity.position, entity.position)
        nationality = {"Sweden": "Swedish", "Finland": "Finnish", "Canada": "Canadian", "United States": "American"}.get(entity.nationality, entity.nationality)
        return f"{question.rstrip(' ?')} concerning {nationality} {position} {entity.canonical_name}?", "public_player_subject"
    # Live-event continuation metadata is attached to Scout-generated
    # investigative prompts. Preserve the originating team only when the new
    # request still reads like one of those contextual continuations; do not
    # leak the prior subject into an unrelated question.
    continuation_language = (
        r"\b(these|those|this|that|their|they|them)\b",
        r"\bthe team(?:'s|’s)\b",
        r"\blatest roster moves?\b",
        r"\bplayer developments? in (?:this|the) coverage\b",
        r"\bthemes? across these stories\b",
    )
    if not any(re.search(pattern, question, re.I) for pattern in continuation_language):
        return question, "ignored"
    # A named entity in the new request takes precedence over the old subject.
    from Knowledge.Intelligence.Entities.entity_registry import entities_by_type
    for team in entities_by_type("team"):
        if any(re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", question, re.I) for alias in searchable_names(team) if len(alias) >= 4):
            return question, "explicit_subject"
    return f"{question.rstrip(' ?')} in recent {entity.canonical_name} news?", "public_team_subject"


def execute_request(request: AthenaRequest) -> Dict[str, Any]:
    question = str(request.question or "").strip()
    mode = str(request.mode or "fantasy").strip().lower()
    if mode not in {"public", "fantasy"}:
        raise ValueError("mode must be public or fantasy")
    sections = tuple(str(section).strip() for section in (request.sections or ()) if str(section).strip())
    effective_question, continuation_status = _continued_question(question, mode, request.continuation)

    from Athena.intent_resolution import select_executable_route
    from Athena.execution_registry import SPECIALISTS, execute_specialist

    route, selected_by = select_executable_route(effective_question, mode)
    if continuation_status == "resolved_pending_inquiry":
        route = "public_player_investigation"
        selected_by = "resolved_entity_pending_inquiry"
    if continuation_status == "public_player_subject":
        from Athena.public_identity import resolve_public_player
        match = resolve_public_player(effective_question)
        if match is not None and match.entity is not None and match.entity.entity_id == request.continuation.get("subject_entity_id"):
            from Athena.intent_planner import comparison_semantics
            if comparison_semantics(question)["class"] == "temporal" or (
                "current production" in question.casefold() and "baseline" in question.casefold()
            ):
                route = "public_player_temporal_comparison"
                selected_by = "continued_public_identity"
            elif route not in {"public_player_comparison", "public_player_temporal_comparison"}:
                from Reasoning.public_player_questions import classify_player_question
                inquiry = classify_player_question(question)
                route = "public_player_identity" if inquiry == "profile" and not question.rstrip().endswith("?") else "public_player_investigation"
                selected_by = "continued_public_identity"
    effective_mode = "public" if route and SPECIALISTS[route].mode == "public" else mode
    context = request.context
    if context is None:
        from Scout.conversation.context import load_context
        context = load_context()
    # Athena owns question-scoped evidence acquisition. Attach the bundle before
    # specialist execution so every consumer sees the same canonical evidence
    # instead of independently reacquiring or falling back to seed material.
    from Athena.evidence_bundle import build_request_evidence
    request_evidence = build_request_evidence(effective_question, mode=effective_mode, route=route)
    try:
        setattr(context, "request_evidence", request_evidence)
    except (AttributeError, TypeError):
        # Minimal immutable test/adaptor contexts may not accept runtime fields.
        # Real ScoutContext instances do; specialists remain compatible with
        # contexts that predate the request-evidence handoff.
        pass
    if route:
        answer = execute_specialist(route, context, effective_question, mode=effective_mode)
        if answer is None:
            raise RuntimeError(f"Registered Athena specialist could not execute: {route}")
        owner = "athena_registered_specialist"
    else:
        # Unported routes remain operational and explicitly visible as fallback.
        from Athena.specialist_compatibility import execute_existing_specialist
        answer = execute_existing_specialist(effective_question, mode=mode, context=context)
        owner = "legacy_scout_specialist_adapter"
    if not isinstance(answer, dict):
        raise TypeError("Athena specialist returned a non-dictionary answer")
    if route == "live_event_intelligence" and answer.get("suggested_prompts"):
        import re
        from Knowledge.Intelligence.Entities.entity_registry import entities_by_type, searchable_names
        subjects = [team for team in entities_by_type("team") if any(
            re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", effective_question, re.I)
            for alias in searchable_names(team) if len(alias) >= 4
        )]
        if len(subjects) == 1:
            answer["continuation"] = {"origin_intent": route, "subject_entity_id": subjects[0].entity_id}
    if answer.get("intent") == "public_player_profile" and answer.get("suggested_prompts"):
        profile = answer.get("developer", {}).get("public_player_profile") if isinstance(answer.get("developer"), dict) else None
        from Knowledge.Intelligence.Entities.entity_registry import find_by_id
        entity = find_by_id(str(profile.get("entity_id") or "")) if isinstance(profile, dict) else None
        if entity is not None and entity.entity_type == "player":
            answer["continuation"] = {"origin_intent": "public_player_profile", "subject_entity_id": entity.entity_id}
    developer = answer.setdefault("developer", {})
    if not isinstance(developer, dict):
        developer = {}
        answer["developer"] = developer
    developer["athena_request"] = {
        "version": ATHENA_VERSION,
        "boundary": "Athena.ask",
        "execution_owner": owner,
        "mode": effective_mode,
        "requested_sections": list(sections),
        "selected_route": route or answer.get("intent", ""),
        "selected_by": selected_by,
        "handler_module": SPECIALISTS[route].module if route else "Scout.conversation.router",
        "handler_executable": bool(route),
        "evidence_readiness": str(request_evidence.get("status") or "not_required"),
        "selected_intent": answer.get("intent", ""),
        "continuation_status": continuation_status,
    }
    return answer
