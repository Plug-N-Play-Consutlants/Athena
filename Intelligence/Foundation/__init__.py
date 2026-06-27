"""Multi-sport intelligence foundation exports."""
from .modules import (
    INTELLIGENCE_FOUNDATION_VERSION,
    IntelligenceModule,
    IntelligenceRegistry,
    seed_intelligence_registry,
    select_intelligence_modules,
    capability_matrix,
    studio_intelligence_diagnostics,
)

__all__ = [
    "INTELLIGENCE_FOUNDATION_VERSION",
    "IntelligenceModule",
    "IntelligenceRegistry",
    "seed_intelligence_registry",
    "select_intelligence_modules",
    "capability_matrix",
    "studio_intelligence_diagnostics",
]
