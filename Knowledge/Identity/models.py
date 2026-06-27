"""Unified identity models for Athena cross-sport knowledge graph.

This layer is intentionally provider-neutral. Providers may contribute records,
but Athena resolves identity against sport, league, canonical entity type, source
confidence, aliases, and external identifiers rather than a provider-specific key.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Tuple

IDENTITY_MODEL_VERSION = "0.5.3.2.0"


@dataclass(frozen=True)
class ExternalIdentifier:
    namespace: str
    value: str
    confidence: float = 1.0

    def key(self) -> str:
        return f"{self.namespace.strip().lower()}:{self.value.strip().lower()}"

    def to_dict(self) -> Dict[str, Any]:
        return {"namespace": self.namespace, "value": self.value, "confidence": self.confidence}


@dataclass(frozen=True)
class IdentityEntity:
    entity_id: str
    entity_type: str
    canonical_name: str
    sport: str
    league: str
    provider_neutral: bool = True
    team_id: str = ""
    position: str = ""
    status: str = "active"
    aliases: Tuple[str, ...] = field(default_factory=tuple)
    external_ids: Tuple[ExternalIdentifier, ...] = field(default_factory=tuple)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def normalized_names(self) -> Tuple[str, ...]:
        names = [self.canonical_name, *self.aliases]
        return tuple(sorted({_normalize_text(name) for name in names if _normalize_text(name)}))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "canonical_name": self.canonical_name,
            "sport": self.sport,
            "league": self.league,
            "provider_neutral": self.provider_neutral,
            "team_id": self.team_id,
            "position": self.position,
            "status": self.status,
            "aliases": list(self.aliases),
            "external_ids": [item.to_dict() for item in self.external_ids],
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class IdentityRelationship:
    subject_id: str
    predicate: str
    object_id: str
    confidence: float = 1.0
    source: str = "athena.identity"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def signature(self) -> str:
        return f"{self.subject_id}|{self.predicate}|{self.object_id}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject_id": self.subject_id,
            "predicate": self.predicate,
            "object_id": self.object_id,
            "confidence": self.confidence,
            "source": self.source,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class IdentityResolution:
    query: str
    sport: str = ""
    league: str = ""
    matches: Tuple[IdentityEntity, ...] = field(default_factory=tuple)
    ambiguous: bool = False
    confidence: float = 0.0
    reason: str = ""

    @property
    def best_match(self) -> IdentityEntity | None:
        return self.matches[0] if self.matches and not self.ambiguous else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "sport": self.sport,
            "league": self.league,
            "matches": [item.to_dict() for item in self.matches],
            "ambiguous": self.ambiguous,
            "confidence": self.confidence,
            "reason": self.reason,
            "best_match_id": self.best_match.entity_id if self.best_match else "",
        }


@dataclass(frozen=True)
class IdentityGraphDiagnostics:
    version: str
    entity_count: int
    relationship_count: int
    sports: Tuple[str, ...]
    leagues: Tuple[str, ...]
    entity_types: Dict[str, int]
    provider_neutral: bool
    ambiguous_names: Dict[str, List[str]] = field(default_factory=dict)
    warnings: Tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "entity_count": self.entity_count,
            "relationship_count": self.relationship_count,
            "sports": list(self.sports),
            "leagues": list(self.leagues),
            "entity_types": dict(self.entity_types),
            "provider_neutral": self.provider_neutral,
            "ambiguous_names": {name: list(ids) for name, ids in self.ambiguous_names.items()},
            "warnings": list(self.warnings),
        }


def _normalize_text(value: str) -> str:
    return " ".join(str(value or "").strip().lower().replace("-", " ").split())


def normalized_key(*parts: str) -> str:
    return ":".join(_normalize_text(part).replace(" ", "_") for part in parts if _normalize_text(part))


def dedupe_relationships(items: Iterable[IdentityRelationship]) -> Tuple[IdentityRelationship, ...]:
    by_signature: Dict[str, IdentityRelationship] = {}
    for item in items:
        current = by_signature.get(item.signature())
        if current is None or item.confidence > current.confidence:
            by_signature[item.signature()] = item
    return tuple(by_signature.values())
