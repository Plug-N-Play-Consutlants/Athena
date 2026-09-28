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


_NATIONALITY_TERMS = {
    "sweden": "swedish", "finland": "finnish", "canada": "canadian",
    "united states": "american", "germany": "german",
}
_POSITION_TERMS = {
    "D": ("defenseman", "defenceman", "defender"),
    "C": ("center", "centre"),
    "LW": ("left wing", "left winger"),
    "RW": ("right wing", "right winger"),
    "G": ("goaltender", "goalie"),
}


def resolve_qualified_player(question: str) -> EntityMatch | None:
    """Resolve a named public player with explicit role/nationality qualifiers.

    Matching name text alone never overrides conflicting qualifiers. A short
    nickname is accepted only when it is the entire query, to avoid incidental
    substring matches in a longer question.
    """
    query = clean_entity_phrase(question)
    normalized = normalize_name(query)
    if not normalized:
        return None
    players = [entity for entity in all_entities() if entity.entity_type == "player"]
    named = []
    for entity in players:
        names = [name for name in searchable_names(entity) if name]
        matches = [name for name in names if (len(normalize_name(name).split()) >= 2 or normalize_name(name) == normalized)
                   and re.search(r"(?<!\w)" + re.escape(normalize_name(name)) + r"(?!\w)", normalized)]
        if matches:
            named.append((entity, max(matches, key=len)))
    if not named:
        return None
    # Only treat an entire bare name as a request when it resolves uniquely.
    full_name = [entity for entity, alias in named if normalize_name(alias) == normalized]
    if len(full_name) == 1:
        return EntityMatch(query, full_name[0], 1.0, "resolved", matched_alias=query)

    requested_nationalities = {term for term in _NATIONALITY_TERMS.values() if re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", normalized)}
    requested_positions = {position for position, terms in _POSITION_TERMS.items() if any(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", normalized) for term in terms)}
    if not requested_nationalities and not requested_positions:
        return None
    qualified = [entity for entity, _ in named
                 if (not requested_nationalities or _NATIONALITY_TERMS.get(entity.nationality.lower(), "") in requested_nationalities)
                 and (not requested_positions or entity.position in requested_positions)]
    if len(qualified) == 1:
        return EntityMatch(query, qualified[0], 0.95, "qualified_resolved", matched_alias=qualified[0].canonical_name)
    return EntityMatch(query, None, 0.0, "qualification_unresolved", candidates=[entity for entity, _ in named])
