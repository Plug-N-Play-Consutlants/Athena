"""Event Intelligence package.

Knowledge owns normalized event facts. Engine and Reasoning layers consume these
facts to produce conclusions, impact propagation and Scout-ready explanations.
"""

from Knowledge.Events.models import EventRecord, EventSourceProfile, EventEvidence, EventRegistry
from Knowledge.Events.registry import EVENT_TYPES, seed_event_registry, source_registry_summary, canonical_event_type, canonical_event_types
from Knowledge.Events.normalizer import normalize_event_payload, canonical_event_payload
from Knowledge.Events.feeds import FeedDefinition, FeedHealth, FeedRegistry, seed_feed_registry
from Knowledge.Events.acquisition import FeedResult, StaticPayloadConnector, acquire_events
from Knowledge.Events.evidence_fusion import EvidenceFusionEngine, FusedEvidence, FusedEvidenceRecord, FusionResult, SourceConfidenceProfile, event_fusion_key, event_signature, fuse_event_evidence, fuse_events

from Knowledge.Events.live_sources import (
    LIVE_EVENT_SOURCE_VERSION,
    LiveSourceProfile,
    LiveSourceRegistry,
    LiveRssConnector,
    parse_rss_items,
    classify_rss_event_type,
    seed_live_feed_registry,
    seed_live_source_registry,
    seed_live_connector_registry,
    acquire_live_rss_events,
    acquire_live_rss_sample,
    live_event_source_summary,
    sample_rss_payload,
)

from Knowledge.Events.live_intelligence import (
    LIVE_INTELLIGENCE_CONSUMPTION_VERSION,
    is_recent_event_query,
    select_live_evidence,
    live_intelligence_diagnostics,
)

__all__ = [
    "EVENT_TYPES",
    "EventRecord",
    "EventSourceProfile",
    "EventEvidence",
    "EventRegistry",
    "seed_event_registry",
    "source_registry_summary",
    "normalize_event_payload",
    "canonical_event_payload",
    "canonical_event_types",
    "canonical_event_type",
    "FeedDefinition",
    "FeedHealth",
    "FeedRegistry",
    "seed_feed_registry",
    "FeedResult",
    "StaticPayloadConnector",
    "acquire_events",
    "EvidenceFusionEngine",
    "FusedEvidenceRecord",
    "FusionResult",
    "event_fusion_key",
    "fuse_event_evidence",
    "FusedEvidence",
    "SourceConfidenceProfile",
    "event_signature",
    "fuse_events",
    "LIVE_EVENT_SOURCE_VERSION",
    "LiveSourceProfile",
    "live_intelligence_diagnostics",
    "select_live_evidence",
    "is_recent_event_query",
    "LIVE_INTELLIGENCE_CONSUMPTION_VERSION",
]
