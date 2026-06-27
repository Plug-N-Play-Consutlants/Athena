"""Evidence engine namespace.

Evidence Fusion currently lives in Knowledge.Events because it binds to event
facts. This namespace provides the stable Engine-level import surface for future
cross-domain evidence systems.
"""
from __future__ import annotations

from Knowledge.Events.evidence_fusion import (
    EvidenceFusionEngine,
    EvidenceObservation,
    FusedEvidenceRecord,
    FusionResult,
    SourceConfidenceProfile,
    evidence_fusion_summary,
    event_fusion_key,
    fuse_event_evidence,
)

EVIDENCE_ENGINE_VERSION = "0.5.2.0.0"

__all__ = [
    "EVIDENCE_ENGINE_VERSION",
    "EvidenceFusionEngine",
    "EvidenceObservation",
    "FusedEvidenceRecord",
    "FusionResult",
    "SourceConfidenceProfile",
    "evidence_fusion_summary",
    "event_fusion_key",
    "fuse_event_evidence",
]
