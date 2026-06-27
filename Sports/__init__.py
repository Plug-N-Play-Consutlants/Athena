"""Sport metadata registry for Athena."""
from .registry import (
    SPORT_REGISTRY_VERSION,
    SportDefinition,
    SportRegistry,
    seed_sport_registry,
    sport_registry_diagnostics,
)

__all__ = [
    "SPORT_REGISTRY_VERSION",
    "SportDefinition",
    "SportRegistry",
    "seed_sport_registry",
    "sport_registry_diagnostics",
]
