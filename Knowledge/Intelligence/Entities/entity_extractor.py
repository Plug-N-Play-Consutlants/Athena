"""Entity extraction and resolution for PIF-1 Build 001."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Dict, List

from .entity_registry import PublicEntity, all_entities, searchable_names
from .fuzzy_match import normalize_name, similarity

_STOP_PHRASES = [
    "tell me about", "analyze", "analyse", "compare", "who is", "what about",
    "give me the rundown on", "show me", "profile", "evaluate", "is", "any good",
]

_CONNECTORS = re.compile(r"\b(and|vs\.?|versus|with|to)\b", re.I)


@dataclass(frozen=True)
class EntityMatch:
    query: str
    entity: PublicEntity | None
    confidence: float
    status: str
    candidates: List[PublicEntity] = field(default_factory=list)
    matched_alias: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "query": self.query,
            "status": self.status,
            "confidence": self.confidence,
            "matched_alias": self.matched_alias,
            "entity": self.entity.to_dict() if self.entity else None,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }


def clean_entity_phrase(question: str) -> str:
    text = (question or "").strip().strip(" .?!\"'")
    lowered = text.lower()
    for phrase in _STOP_PHRASES:
        if lowered.startswith(phrase):
            text = text[len(phrase):].strip(" .?!\"'")
            lowered = text.lower()
            break
    return text


def split_entity_phrases(question: str) -> List[str]:
    cleaned = clean_entity_phrase(question)
    parts = [part.strip(" .?!\"'") for part in _CONNECTORS.split(cleaned) if part and not _CONNECTORS.fullmatch(part)]
    parts = [part for part in parts if part]
    return parts or ([cleaned] if cleaned else [])


def resolve_entity(phrase: str, preferred_type: str = "") -> EntityMatch:
    query = clean_entity_phrase(phrase)
    if not query:
        return EntityMatch(query=query, entity=None, confidence=0.0, status="no_query")

    entities = all_entities()
    if preferred_type:
        filtered = [entity for entity in entities if entity.entity_type == preferred_type]
        if filtered:
            entities = filtered

    scored: List[tuple[PublicEntity, float, str]] = []
    for entity in entities:
        best_alias = ""
        best_score = 0.0
        for name in searchable_names(entity):
            score = similarity(query, name)
            if score > best_score:
                best_alias = name
                best_score = score
        if best_score >= 0.74:
            scored.append((entity, best_score, best_alias))

    scored.sort(key=lambda item: item[1], reverse=True)
    if not scored:
        return EntityMatch(query=query, entity=None, confidence=0.0, status="not_found")

    # Same-name duplicate entities must be surfaced instead of collapsed.
    top_score = scored[0][1]
    close = [item for item in scored if top_score - item[1] <= 0.04]
    canonical_names = {normalize_name(item[0].canonical_name) for item in close}
    if len(close) > 1 and len(canonical_names) == 1:
        return EntityMatch(query=query, entity=None, confidence=round(top_score, 4), status="ambiguous", candidates=[item[0] for item in close], matched_alias=scored[0][2])

    # Exact ambiguous alias, like "Sebastian Aho", also needs disambiguation.
    exact_alias_matches = []
    normalized_query = normalize_name(query)
    for entity in entities:
        for name in searchable_names(entity):
            if normalize_name(name) == normalized_query:
                exact_alias_matches.append(entity)
                break
    if len(exact_alias_matches) > 1:
        return EntityMatch(query=query, entity=None, confidence=1.0, status="ambiguous", candidates=exact_alias_matches, matched_alias=query)

    entity, score, alias = scored[0]
    status = "resolved" if score >= 0.9 else "fuzzy_resolved"
    return EntityMatch(query=query, entity=entity, confidence=round(score, 4), status=status, matched_alias=alias)


def extract_entities(question: str, preferred_type: str = "") -> List[EntityMatch]:
    return [resolve_entity(part, preferred_type=preferred_type) for part in split_entity_phrases(question)]
