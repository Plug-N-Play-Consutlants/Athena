"""Sport-aware provider-neutral identity resolution."""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Iterable

from .models import IdentityEntity, IdentityResolution
from .registry import CrossSportIdentityRegistry, seed_identity_registry


def resolve_identity(
    query: str,
    sport: str = "",
    league: str = "",
    entity_type: str = "",
    registry: CrossSportIdentityRegistry | None = None,
) -> IdentityResolution:
    registry = registry or seed_identity_registry()
    query_text = str(query or "").strip()
    if not query_text:
        return IdentityResolution(query=query_text, sport=sport, league=league, reason="empty query")

    candidates = list(registry.search_name(query_text, sport=sport, league=league, entity_type=entity_type))
    if not candidates:
        candidates = _fuzzy_candidates(query_text, registry.all_entities(), sport=sport, league=league, entity_type=entity_type)

    candidates = sorted(candidates, key=lambda entity: _score(query_text, entity), reverse=True)
    if not candidates:
        return IdentityResolution(query=query_text, sport=sport, league=league, reason="no identity match")

    top_score = _score(query_text, candidates[0])
    tied = [entity for entity in candidates if abs(_score(query_text, entity) - top_score) < 0.02]
    canonical_duplicate = len({entity.entity_id for entity in candidates if entity.canonical_name.lower() == candidates[0].canonical_name.lower()}) > 1
    ambiguous = len(tied) > 1 or (canonical_duplicate and not sport and not league)
    reason = "ambiguous identity requires sport/league/entity context" if ambiguous else "resolved by sport-aware identity registry"
    return IdentityResolution(
        query=query_text,
        sport=sport,
        league=league,
        matches=tuple(candidates[:5]),
        ambiguous=ambiguous,
        confidence=round(top_score, 3),
        reason=reason,
    )


def resolve_external_identity(namespace: str, value: str, registry: CrossSportIdentityRegistry | None = None) -> IdentityResolution:
    registry = registry or seed_identity_registry()
    entity = registry.by_external_id(namespace, value)
    query = f"{namespace}:{value}"
    if not entity:
        return IdentityResolution(query=query, reason="no external identity match")
    return IdentityResolution(query=query, sport=entity.sport, league=entity.league, matches=(entity,), confidence=1.0, reason="resolved by external identifier")


def _fuzzy_candidates(query: str, entities: Iterable[IdentityEntity], sport: str = "", league: str = "", entity_type: str = "") -> list[IdentityEntity]:
    sport_key = sport.lower().strip()
    league_key = league.lower().strip()
    type_key = entity_type.lower().strip()
    matches: list[IdentityEntity] = []
    for entity in entities:
        if sport_key and entity.sport.lower() != sport_key:
            continue
        if league_key and entity.league.lower() != league_key:
            continue
        if type_key and entity.entity_type.lower() != type_key:
            continue
        if _score(query, entity) >= 0.72:
            matches.append(entity)
    return matches


def _score(query: str, entity: IdentityEntity) -> float:
    q = " ".join(query.strip().lower().replace("-", " ").split())
    scores = [SequenceMatcher(None, q, name).ratio() for name in entity.normalized_names()]
    return max(scores or [0.0])
