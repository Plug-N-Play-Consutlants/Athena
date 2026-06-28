"""Core AthenaEngine exports."""

try:
    from .capability_registry import (
        CAPABILITY_REGISTRY_VERSION,
        CapabilityMetadata,
        CapabilityRegistry,
        capability_registry_diagnostics,
        discover_capabilities,
        seed_capability_registry,
    )
except Exception:  # pragma: no cover - optional during partial imports
    pass
try:
    from .execution_trace import (
        EXECUTION_TRACE_VERSION,
        CapabilityTrace,
        ExecutionStage,
        ExecutionTrace,
        create_execution_trace,
        execution_trace_diagnostics,
        persist_execution_trace,
        sample_execution_trace,
    )
except Exception:  # pragma: no cover - optional during partial imports
    pass

try:
    from .composition_audit import (
        COMPOSITION_AUDIT_VERSION,
        CompositionAuditRecord,
        CompositionAuditReport,
        audit_composition,
        composition_audit_diagnostics,
        sample_composition_audit_report,
    )
except Exception:  # pragma: no cover - optional during partial imports
    pass

try:
    from .acceptance_explorer import (
        ACCEPTANCE_EXPLORER_VERSION,
        AcceptanceExplorerReport,
        AcceptanceExplorerSection,
        acceptance_explorer_diagnostics,
        build_acceptance_report,
        sample_acceptance_report,
        sample_acceptance_trace,
    )
except Exception:  # pragma: no cover - optional during partial imports
    pass
