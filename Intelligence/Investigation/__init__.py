"""Adaptive investigation strategy, runtime integration, and bounded working state."""
from .strategy import INVESTIGATION_STRATEGY_VERSION, InvestigationStrategy, InvestigationStrategyRegistry, select_investigation_strategy, strategy_diagnostics
from .state import INVESTIGATION_STATE_VERSION, InvestigationState, InvestigationSessionRegistry
from .context_policy import ContextPriority, ContextPolicy
from .composition_contract import CompositionContract
from .orchestrator import InvestigationPlan, build_investigation_plan, investigation_diagnostics
from .evidence_fallback import EVIDENCE_FALLBACK_VERSION, EvidenceCandidate, EvidenceSelection, select_recent_relevant_evidence
from .runtime_bridge import RUNTIME_INTEGRATION_VERSION, InvestigationRuntimeContext, prepare_runtime_context, record_runtime_outcome
__all__ = [name for name in globals() if not name.startswith('_')]
