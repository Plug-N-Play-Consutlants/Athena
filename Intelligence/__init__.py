"""Intelligence layer modules."""
from Intelligence.Foundation import (
    INTELLIGENCE_FOUNDATION_VERSION,
    IntelligenceModule,
    IntelligenceRegistry,
    seed_intelligence_registry,
    select_intelligence_modules,
    capability_matrix,
    studio_intelligence_diagnostics,
)

from Intelligence.Explainability import (
    EXPLAINABLE_INTELLIGENCE_VERSION,
    EvidenceItem,
    EvidenceBundle,
    ReasoningStep,
    ReasoningTrace,
    ConfidenceReport,
    ExplainabilityResult,
)
from Intelligence.Pipeline import (
    EXPLAINABLE_PIPELINE_VERSION,
    execute_explainable_intelligence,
    studio_explainability_diagnostics,
)
from Intelligence.Confidence import (
    CONFIDENCE_PROPAGATION_VERSION,
    propagate_confidence,
)

from Intelligence.Reasoning import (
    CROSS_SPORT_REASONING_VERSION,
    ReasoningAdapter,
    ReasoningAdapterRegistry,
    FusedEvidence,
    AmbiguityCandidate,
    AmbiguityResolution,
    CrossSportComparison,
    CrossSportReasoningResult,
    seed_reasoning_adapter_registry,
    adapter_registry_diagnostics,
    reason_cross_sport_query,
    studio_reasoning_diagnostics,
)

from Intelligence.Runtime import (
    RUNTIME_ORCHESTRATION_VERSION,
    RuntimeStage,
    RuntimeTrace,
    EvidenceContribution,
    normalize_contributions,
    run_runtime_trace,
    studio_runtime_observability_diagnostics,
)

__all__ = [
    "INTELLIGENCE_FOUNDATION_VERSION",
    "IntelligenceModule",
    "IntelligenceRegistry",
    "seed_intelligence_registry",
    "select_intelligence_modules",
    "capability_matrix",
    "studio_intelligence_diagnostics",
    "EXPLAINABLE_INTELLIGENCE_VERSION",
    "EXPLAINABLE_PIPELINE_VERSION",
    "CONFIDENCE_PROPAGATION_VERSION",
    "EvidenceItem",
    "EvidenceBundle",
    "ReasoningStep",
    "ReasoningTrace",
    "ConfidenceReport",
    "ExplainabilityResult",
    "execute_explainable_intelligence",
    "studio_explainability_diagnostics",
    "propagate_confidence",
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
    "RUNTIME_ORCHESTRATION_VERSION",
    "RuntimeStage",
    "RuntimeTrace",
    "EvidenceContribution",
    "normalize_contributions",
    "run_runtime_trace",
    "studio_runtime_observability_diagnostics",
]
