"""Cross-sport identity graph construction and diagnostics."""
from __future__ import annotations

from typing import Dict, Iterable, Tuple

from .models import IDENTITY_MODEL_VERSION, IdentityGraphDiagnostics, IdentityRelationship, dedupe_relationships
from .registry import CrossSportIdentityRegistry, seed_identity_registry


def build_identity_relationships(registry: CrossSportIdentityRegistry | None = None) -> tuple[IdentityRelationship, ...]:
    registry = registry or seed_identity_registry()
    relationships: list[IdentityRelationship] = []
    for entity in registry.all_entities():
        if entity.entity_type == "league":
            relationships.append(IdentityRelationship(entity.entity_id, "belongs_to_sport", f"sport.{entity.sport}", 1.0))
        if entity.entity_type == "team":
            relationships.append(IdentityRelationship(entity.entity_id, "competes_in", f"league.{entity.league.lower()}", 1.0))
        if entity.entity_type == "player":
            if entity.team_id:
                relationships.append(IdentityRelationship(entity.entity_id, "plays_for", entity.team_id, 0.95))
            relationships.append(IdentityRelationship(entity.entity_id, "eligible_in_league", f"league.{entity.league.lower()}", 1.0))
        for external in entity.external_ids:
            relationships.append(IdentityRelationship(entity.entity_id, "has_external_identifier", external.key(), external.confidence, metadata={"namespace": external.namespace}))
    return dedupe_relationships(relationships)


def build_cross_sport_identity_graph(registry: CrossSportIdentityRegistry | None = None) -> Dict[str, object]:
    registry = registry or seed_identity_registry()
    relationships = build_identity_relationships(registry)
    return {
        "version": IDENTITY_MODEL_VERSION,
        "nodes": [entity.to_dict() for entity in registry.all_entities()],
        "relationships": [relationship.to_dict() for relationship in relationships],
        "diagnostics": identity_graph_diagnostics(registry, relationships).to_dict(),
    }


def identity_graph_diagnostics(
    registry: CrossSportIdentityRegistry | None = None,
    relationships: Iterable[IdentityRelationship] | None = None,
) -> IdentityGraphDiagnostics:
    registry = registry or seed_identity_registry()
    stats = registry.stats()
    rels = tuple(relationships if relationships is not None else build_identity_relationships(registry))
    warnings: list[str] = []
    if stats.get("ambiguous_names"):
        warnings.append("Ambiguous names exist and require disambiguation context.")
    if not stats.get("provider_neutral"):
        warnings.append("One or more identity records are provider-coupled.")
    return IdentityGraphDiagnostics(
        version=IDENTITY_MODEL_VERSION,
        entity_count=int(stats["entities"]),
        relationship_count=len(rels),
        sports=tuple(stats["sports"]),
        leagues=tuple(stats["leagues"]),
        entity_types=dict(stats["by_type"]),
        provider_neutral=bool(stats["provider_neutral"]),
        ambiguous_names={name: list(ids) for name, ids in dict(stats["ambiguous_names"]).items()},
        warnings=tuple(warnings),
    )


def studio_identity_graph_diagnostics() -> Dict[str, object]:
    """Stable Studio-facing diagnostic payload."""
    graph = build_cross_sport_identity_graph()
    diagnostics = graph["diagnostics"]
    return {
        "panel": "identity_graph",
        "status": "warn" if diagnostics.get("warnings") else "pass",  # ambiguity is expected, not failure
        "version": IDENTITY_MODEL_VERSION,
        "diagnostics": diagnostics,
        "sample_nodes": graph["nodes"][:5],
        "sample_relationships": graph["relationships"][:5],
    }
