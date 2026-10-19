"""Athena's question execution boundary for Scout and future experiences."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable
from time import perf_counter

from Core.version import ATHENA_VERSION


@dataclass(frozen=True)
class AthenaRequest:
    question: str
    mode: str = "fantasy"
    context: Any = None
    sections: Iterable[str] = ()
    continuation: Any = None


class _RequestEvidenceContext:
    """Read-through adapter for immutable legacy contexts."""

    __slots__ = ("_context", "request_evidence")

    def __init__(self, context: Any, request_evidence: Dict[str, Any]) -> None:
        self._context = context
        self.request_evidence = request_evidence

    def __getattr__(self, name: str) -> Any:
        return getattr(self._context, name)


def _continued_question(question: str, mode: str, continuation: Any) -> tuple[str, str]:
    """Use an advisory subject hint; specialists still acquire their own evidence."""
    if mode != "public" or not isinstance(continuation, dict):
        return question, "none"
    origin = continuation.get("origin_intent")
    if origin not in {"live_event_intelligence", "public_player_profile", "public_entity_disambiguation", "public_nhl_decision_inquiry"}:
        return question, "ignored"
    if origin == "public_nhl_decision_inquiry":
        import re
        subject = str(continuation.get("subject") or "").strip()
        if subject not in {"Toronto Maple Leafs"}:
            return question, "ignored_unverified_decision_subject"
        if not re.search(r"\b(those|these|that|this|recommendations|still|first.round pick|left wing|does it change)\b", question, re.I):
            return question, "ignored_unrelated_decision_followup"
        if re.search(r"\b(toronto|maple leafs|leafs)\b", question, re.I):
            return question, "explicit_decision_subject"
        return f"Regarding the Toronto Maple Leafs trade options: {question}", "continued_nhl_decision_subject"
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
    started = perf_counter()
    question = str(request.question or "").strip()
    mode = str(request.mode or "fantasy").strip().lower()
    if mode not in {"public", "fantasy"}:
        raise ValueError("mode must be public or fantasy")
    sections = tuple(str(section).strip() for section in (request.sections or ()) if str(section).strip())
    effective_question, continuation_status = _continued_question(question, mode, request.continuation)

    from Athena.inquiry_objectives import decompose_inquiry, assess_objective_coverage
    inquiry_plan = decompose_inquiry(effective_question)
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
    evidence_started = perf_counter()
    request_evidence = build_request_evidence(effective_question, mode=effective_mode, route=route)
    evidence_ms = round((perf_counter() - evidence_started) * 1000, 2)
    evidence_attached = False
    evidence_transport = "none"
    execution_context = context
    try:
        setattr(context, "request_evidence", request_evidence)
        evidence_attached = True
        evidence_transport = "context_attribute"
    except (AttributeError, TypeError):
        if route:
            execution_context = _RequestEvidenceContext(context, request_evidence)
            evidence_attached = True
            evidence_transport = "read_through_context_adapter"
    specialist_started = perf_counter()
    if route:
        answer = execute_specialist(route, execution_context, effective_question, mode=effective_mode)
        if answer is None:
            raise RuntimeError(f"Registered Athena specialist could not execute: {route}")
        owner = "athena_registered_specialist"
    else:
        # Unported routes remain operational and explicitly visible as fallback.
        from Athena.specialist_compatibility import execute_existing_specialist
        answer = execute_existing_specialist(effective_question, mode=mode, context=context)
        owner = "legacy_scout_specialist_adapter"
    specialist_ms = round((perf_counter() - specialist_started) * 1000, 2)
    if not isinstance(answer, dict):
        raise TypeError("Athena specialist returned a non-dictionary answer")
    if route == "public_nhl_decision_inquiry" and "toronto" in effective_question.casefold():
        answer["continuation"] = {"origin_intent": route, "subject": "Toronto Maple Leafs"}
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
    # Reconcile verified fallback acquisitions before calculating completion and
    # publishing readiness. Preserve independent missing requirements.
    from Athena.evidence_reconciliation import reconcile_evidence
    evidence_reconciliation = reconcile_evidence(request_evidence, answer)
    team_consumption = developer.get("team_evidence_consumption")
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
    # Diagnostic-only execution record. No question text, credentials, raw evidence,
    # or private league data are duplicated into the trace. "selected" and
    # "invoked" are deliberately distinct from "registered" and "used".
    evidence_sources = request_evidence.get("sources") if isinstance(request_evidence, dict) else []
    evidence_missing = request_evidence.get("missing") if isinstance(request_evidence, dict) else []
    # Shared completion assessment also powers inquiry_execution.investigate.
    from Athena.completion_assessment import assess_completion
    from Athena.capability_coordination import execute_compatible_support
    capability_coordination = execute_compatible_support(inquiry_plan, route, effective_mode, effective_question, execution_context, answer)
    from Athena.capability_coordination import synthesize_supporting_findings
    synthesis = synthesize_supporting_findings(answer, capability_coordination, effective_question)
    developer["supporting_synthesis"] = synthesis
    developer["capability_coordination"] = capability_coordination
    objective_coverage = assess_objective_coverage(inquiry_plan, request_evidence, answer)
    completion = assess_completion(answer, evidence=request_evidence, question=effective_question)
    developer["inquiry_objectives"] = inquiry_plan
    developer["inquiry_objective_coverage"] = objective_coverage
    completion_state = completion["state"]
    missing_requirements = completion["unresolved_requirements"]
    developer["inquiry_completion"] = completion
    developer["inquiry_execution_trace"] = {
        "schema": "athena.inquiry_trace.v1",
        "version": ATHENA_VERSION,
        "entry": "Athena.request_execution.execute_request",
        "mode": effective_mode,
        "selection": {"route": route or "", "selected_by": selected_by,
                      "registered": bool(route and route in SPECIALISTS)},
        "invocation": {"owner": owner, "route": route or "legacy_fallback",
                       "handler": SPECIALISTS[route].function if route else "execute_existing_specialist",
                       "completed": True, "duration_ms": specialist_ms},
        "evidence": {"status": request_evidence.get("status", "unknown"),
                     "sources": list(evidence_sources) if isinstance(evidence_sources, list) else [],
                     "missing": list(evidence_missing) if isinstance(evidence_missing, list) else [],
                     "attached_to_context": evidence_attached,
                     "transport": evidence_transport,
                     "acquisition_duration_ms": evidence_ms,
                     "specialist_evidence": request_evidence.get("specialist_evidence"),
                     "reconciliation": evidence_reconciliation},
        "objectives": {"count": len(inquiry_plan["objectives"]), "ids": [o["id"] for o in inquiry_plan["objectives"]], "independently_verified": False},
        "capability_coordination": capability_coordination,
        "supporting_synthesis": synthesis,
        "result": {"intent": str(answer.get("intent") or ""),
                   "confidence": answer.get("confidence") if isinstance(answer.get("confidence"), (int, float)) else None,
                   "public_fields_present": [key for key in (
                       "natural_language_response", "public_comment", "response_text",
                       "scout_message", "engine_conclusion") if bool(answer.get(key))],
                   "limitations_present": bool(answer.get("limitations") or answer.get("known_limitations")),
                   "completion_state": completion_state,
                   "unresolved_requirement_count": len(missing_requirements),
                   "inquiry_completeness_verified": completion["inquiry_answered_verified"],
                   "evidence_consumption_verified": bool(
                       isinstance(team_consumption, dict)
                       and team_consumption.get("consumed") is True
                       and team_consumption.get("owner") == "Athena.request_execution"
                   ),
                   "evidence_consumption": team_consumption if isinstance(team_consumption, dict) else None,
                   "specialist_evidence_reported": bool(request_evidence.get("specialist_evidence"))},
        "continuation": continuation_status,
        "total_duration_ms": round((perf_counter() - started) * 1000, 2),
    }
    return answer
