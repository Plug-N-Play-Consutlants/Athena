"""Unified Identity & Cross-Sport Knowledge Graph public API."""
from __future__ import annotations

from .models import (
    IDENTITY_MODEL_VERSION,
    ExternalIdentifier,
    IdentityEntity,
    IdentityGraphDiagnostics,
    IdentityRelationship,
    IdentityResolution,
)
from .registry import CrossSportIdentityRegistry, identity_key_for_provider, seed_identity_registry
from .resolver import resolve_external_identity, resolve_identity
from .graph import (
    build_cross_sport_identity_graph,
    build_identity_relationships,
    identity_graph_diagnostics,
    studio_identity_graph_diagnostics,
)

__all__ = [
    "IDENTITY_MODEL_VERSION",
    "ExternalIdentifier",
    "IdentityEntity",
    "IdentityGraphDiagnostics",
    "IdentityRelationship",
    "IdentityResolution",
    "CrossSportIdentityRegistry",
    "identity_key_for_provider",
    "seed_identity_registry",
    "resolve_external_identity",
    "resolve_identity",
    "build_cross_sport_identity_graph",
    "build_identity_relationships",
    "identity_graph_diagnostics",
    "studio_identity_graph_diagnostics",
]
