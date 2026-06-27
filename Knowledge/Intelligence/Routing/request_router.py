"""PIF-1 public request router.

This module decides intent and entities before any downstream evidence retrieval.
Build 002 adds knowledge-domain guardrails so public mode does not accidentally
answer draft/comparison/player prompts from fantasy data or rulebook packs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List

from Knowledge.Intelligence.Intent.intent_classifier import IntentResult, classify_intent
from Knowledge.Intelligence.Intent.intent_types import IntentType
from Knowledge.Intelligence.Entities.entity_extractor import EntityMatch, extract_entities, resolve_entity

_PLAYER_INTENTS = {IntentType.PLAYER_PROFILE, IntentType.PLAYER_ANALYSIS, IntentType.PLAYER_COMPARISON, IntentType.PROJECTION, IntentType.HISTORICAL_QUESTION}
_TEAM_INTENTS = {IntentType.TEAM_PROFILE, IntentType.TEAM_ANALYSIS, IntentType.TEAM_COMPARISON}

_ALLOWED_DOMAINS: Dict[IntentType, List[str]] = {
    IntentType.PLAYER_PROFILE: ["public_entity_registry", "player_identity", "career_context", "historical_intelligence"],
    IntentType.PLAYER_ANALYSIS: ["public_entity_registry", "player_identity", "career_context", "historical_intelligence", "current_context"],
    IntentType.PLAYER_COMPARISON: ["public_entity_registry", "player_comparison", "career_context", "historical_intelligence", "statistics"],
    IntentType.TEAM_PROFILE: ["public_entity_registry", "team_identity", "team_context"],
    IntentType.TEAM_ANALYSIS: ["public_entity_registry", "team_identity", "team_context", "organizational_context"],
    IntentType.TEAM_COMPARISON: ["public_entity_registry", "team_comparison", "organizational_context"],
    IntentType.TRANSACTION_SUMMARY: ["event_intelligence", "transactions", "news_feeds"],
    IntentType.DRAFT_ANALYSIS: ["draft_intelligence", "prospect_intelligence", "public_entity_registry"],
    IntentType.PROSPECT_ANALYSIS: ["prospect_intelligence", "draft_intelligence", "public_entity_registry"],
    IntentType.NEWS_SUMMARY: ["event_intelligence", "news_feeds", "transactions"],
    IntentType.HISTORICAL_QUESTION: ["historical_intelligence", "public_entity_registry", "records", "awards"],
    IntentType.PROJECTION: ["projection_intelligence", "public_entity_registry", "current_context", "historical_intelligence"],
    IntentType.RULEBOOK_QUESTION: ["rulebook_knowledge", "cba_knowledge", "mou_knowledge"],
    IntentType.GENERAL_DISCUSSION: ["clarification"],
    IntentType.UNKNOWN: ["clarification"],
}

_BLOCKED_PUBLIC_DOMAINS = {
    IntentType.PLAYER_PROFILE: ["fantasy_owner_data", "fantrax_manager_behavior", "rulebook_knowledge"],
    IntentType.PLAYER_ANALYSIS: ["fantasy_owner_data", "fantrax_manager_behavior", "rulebook_knowledge"],
    IntentType.PLAYER_COMPARISON: ["fantasy_owner_data", "fantrax_manager_behavior", "rulebook_knowledge"],
    IntentType.DRAFT_ANALYSIS: ["rulebook_knowledge", "cba_knowledge", "fantasy_owner_data"],
    IntentType.PROSPECT_ANALYSIS: ["rulebook_knowledge", "cba_knowledge", "fantasy_owner_data"],
}


@dataclass(frozen=True)
class PublicRoute:
    question: str
    intent: IntentResult
    entities: List[EntityMatch] = field(default_factory=list)
    route: str = "clarify"
    confidence: float = 0.0
    allowed_domains: List[str] = field(default_factory=list)
    blocked_domains: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "question": self.question,
            "intent": self.intent.to_dict(),
            "entities": [entity.to_dict() for entity in self.entities],
            "route": self.route,
            "confidence": self.confidence,
            "allowed_domains": list(self.allowed_domains),
            "blocked_domains": list(self.blocked_domains),
            "notes": list(self.notes),
        }


def _domains_for(intent_type: IntentType) -> List[str]:
    return list(_ALLOWED_DOMAINS.get(intent_type, ["clarification"]))


def _blocked_for(intent_type: IntentType) -> List[str]:
    return list(_BLOCKED_PUBLIC_DOMAINS.get(intent_type, []))


def _normalize_public_entity_question(question: str) -> str:
    text = (question or "").strip().lower()
    text = re.sub(r"\bleaf['’]?s\b", "leafs", text)
    text = re.sub(r"\bmaple leaf['’]?s\b", "maple leafs", text)
    return text


def analyze_public_request(question: str) -> PublicRoute:
    normalized_question = _normalize_public_entity_question(question)
    intent = classify_intent(normalized_question)
    preferred_type = "team" if intent.intent in _TEAM_INTENTS else "player" if intent.intent in _PLAYER_INTENTS else ""
    entities: List[EntityMatch] = []
    notes: List[str] = []

    if intent.intent == IntentType.PLAYER_COMPARISON:
        entities = extract_entities(normalized_question, preferred_type="player")
        route = "player_comparison"
        notes.append("Public comparison route selected; fantasy owner context is blocked unless explicitly requested.")
    elif intent.intent in _PLAYER_INTENTS:
        entities = [resolve_entity(normalized_question, preferred_type="player")]
        if entities and entities[0].status == "ambiguous":
            route = "disambiguate_entity"
            notes.append("Duplicate public entity name found; Scout should ask the user which entity they mean.")
        elif entities and entities[0].entity:
            route = "player_intelligence"
        else:
            team_match = resolve_entity(normalized_question, preferred_type="team")
            if team_match.entity:
                entities = [team_match]
                route = "team_intelligence"
            elif intent.intent in {IntentType.PROJECTION, IntentType.HISTORICAL_QUESTION}:
                route = "public_intelligence_gap"
            else:
                route = "clarify"
    elif intent.intent == IntentType.TEAM_COMPARISON:
        entities = extract_entities(normalized_question, preferred_type="team")
        route = "team_comparison" if len([match for match in entities if match.entity]) >= 2 else "public_intelligence_gap"
        notes.append("Public team comparison route selected; provider/owner context is blocked unless explicitly requested.")
    elif intent.intent in _TEAM_INTENTS:
        entities = [resolve_entity(normalized_question, preferred_type="team")]
        route = "team_intelligence" if entities and entities[0].entity else "public_intelligence_gap"
    elif intent.intent == IntentType.TRANSACTION_SUMMARY:
        route = "event_intelligence_gap"
    elif intent.intent == IntentType.DRAFT_ANALYSIS:
        route = "draft_intelligence_gap"
        notes.append("Draft intent blocks rulebook/CBA retrieval unless the question explicitly asks for draft rules.")
    elif intent.intent == IntentType.PROSPECT_ANALYSIS:
        route = "prospect_intelligence_gap"
    elif intent.intent == IntentType.RULEBOOK_QUESTION:
        route = "rulebook_knowledge"
    elif intent.intent == IntentType.NEWS_SUMMARY:
        route = "event_intelligence_gap"
    else:
        route = "clarify"

    entity_conf = max([match.confidence for match in entities], default=0.0)
    confidence = round(max(intent.confidence, (intent.confidence + entity_conf) / 2 if entities else intent.confidence), 4)
    return PublicRoute(
        question=question,
        intent=intent,
        entities=entities,
        route=route,
        confidence=confidence,
        allowed_domains=_domains_for(intent.intent),
        blocked_domains=_blocked_for(intent.intent),
        notes=notes,
    )
