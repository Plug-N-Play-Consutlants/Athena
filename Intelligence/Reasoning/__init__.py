"""Cross-sport reasoning engine exports."""
from .models import (
    CROSS_SPORT_REASONING_VERSION,
    ReasoningAdapter,
    FusedEvidence,
    AmbiguityCandidate,
    AmbiguityResolution,
    CrossSportComparison,
    CrossSportReasoningResult,
)
from .adapters import (
    ReasoningAdapterRegistry,
    seed_reasoning_adapter_registry,
    adapter_registry_diagnostics,
)
from .engine import reason_cross_sport_query, studio_reasoning_diagnostics

__all__ = [
    "CROSS_SPORT_REASONING_VERSION",
    "ReasoningAdapter",
    "ReasoningAdapterRegistry",
    "FusedEvidence",
    "AmbiguityCandidate",
    "AmbiguityResolution",
    "CrossSportComparison",
    "CrossSportReasoningResult",
    "seed_reasoning_adapter_registry",
    "adapter_registry_diagnostics",
    "reason_cross_sport_query",
    "studio_reasoning_diagnostics",
]
