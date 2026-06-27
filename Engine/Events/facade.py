"""Reusable Event Engine facade.

The facade centralizes Event Intelligence operations that are algorithmic rather
than factual. It delegates fact ownership to Knowledge.Events, allowing future
Reasoning modules to consume event acquisition/fusion behavior without importing
many lower-level modules directly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from Knowledge.Events.acquisition import ConnectorRegistry, FeedAcquisitionEngine, FeedResult, seed_connector_registry
from Knowledge.Events.evidence_fusion import EvidenceFusionEngine, FusionResult, fuse_event_evidence
from Knowledge.Events.feeds import FeedDefinition, FeedRegistry, discover_feeds, seed_feed_registry
from Knowledge.Events.models import EventRecord
from Engine.EventReasoning.reasoning_engine import EventReasoningEngine
from Engine.EventReasoning.models import EventReasoningBatch
from Knowledge.Events.registry import EVENT_TYPES, seed_event_registry, source_registry_summary
from Knowledge.Events.source_intelligence import SourceRegistry, seed_source_registry
from Knowledge.Events.live_sources import live_event_source_summary, seed_live_feed_registry, seed_live_connector_registry

EVENT_ENGINE_VERSION = "0.5.2.1.1"


@dataclass
class EventEngineFacade:
    """High-level reusable facade for Event Intelligence workflows.

    This class intentionally keeps behavior deterministic and dependency-light.
    It does not perform live network polling. It composes the registries and
    engines already introduced in Epic 5 Sprint 1.
    """

    feed_registry: FeedRegistry = field(default_factory=seed_feed_registry)
    connector_registry: ConnectorRegistry = field(default_factory=seed_connector_registry)
    source_registry: SourceRegistry = field(default_factory=seed_source_registry)

    @property
    def version(self) -> str:
        return EVENT_ENGINE_VERSION

    def summary(self) -> Dict[str, Any]:
        feeds = self.feed_registry.feeds if hasattr(self.feed_registry, "feeds") else {}
        connectors = self.connector_registry.available_types() if hasattr(self.connector_registry, "available_types") else []
        sources = self.source_registry.sources if hasattr(self.source_registry, "sources") else {}
        return {
            "version": self.version,
            "event_types": list(EVENT_TYPES),
            "feed_count": len(feeds),
            "connector_types": list(connectors),
            "source_count": len(sources),
            "source_registry": source_registry_summary(),
            "live_sources": live_event_source_summary(),
            "layer_contract": {
                "knowledge": "facts and registries",
                "engine": "deterministic reusable algorithms",
                "reasoning": "conclusions and explanations",
                "scout": "presentation",
            },
        }

    def discover(
        self,
        *,
        sport: Optional[str] = None,
        league: Optional[str] = None,
        source_id: Optional[str] = None,
        event_type: Optional[str] = None,
        include_unhealthy: bool = False,
    ) -> List[FeedDefinition]:
        feeds = discover_feeds(
            self.feed_registry,
            sport=sport or "multi",
            league=league,
            event_type=event_type,
            include_unhealthy=include_unhealthy,
        )
        if source_id:
            feeds = [feed for feed in feeds if feed.source_id == source_id]
        return feeds

    def live_source_summary(self) -> Dict[str, Any]:
        return live_event_source_summary()

    def acquire_live(self, feed_id: str, *, allow_network: bool = False) -> FeedResult:
        engine = FeedAcquisitionEngine(seed_live_feed_registry(), seed_live_connector_registry(allow_network=allow_network))
        return engine.acquire(feed_id)

    def acquire(self, feed_id: str) -> FeedResult:
        engine = FeedAcquisitionEngine(self.feed_registry, self.connector_registry)
        return engine.acquire(feed_id)

    def acquire_many(self, feed_ids: Iterable[str]) -> List[FeedResult]:
        engine = FeedAcquisitionEngine(self.feed_registry, self.connector_registry)
        return engine.acquire_many(feed_ids)

    def fuse(self, events: Iterable[EventRecord]) -> FusionResult:
        return fuse_event_evidence(events)

    def reason(self, events: Iterable[EventRecord]) -> EventReasoningBatch:
        event_list = list(events)
        fusion_result = self.fuse(event_list)
        return EventReasoningEngine().reason_about_events(event_list, fusion_result)

    def acquire_and_fuse(self, feed_ids: Iterable[str]) -> FusionResult:
        events: List[EventRecord] = []
        for result in self.acquire_many(feed_ids):
            events.extend(result.events)
        return self.fuse(events)

    def acquire_and_reason(self, feed_ids: Iterable[str]) -> EventReasoningBatch:
        events: List[EventRecord] = []
        for result in self.acquire_many(feed_ids):
            events.extend(result.events)
        return self.reason(events)


def build_event_engine(
    feed_registry: Optional[FeedRegistry] = None,
    connector_registry: Optional[ConnectorRegistry] = None,
    source_registry: Optional[SourceRegistry] = None,
) -> EventEngineFacade:
    return EventEngineFacade(
        feed_registry=feed_registry or seed_feed_registry(),
        connector_registry=connector_registry or seed_connector_registry(),
        source_registry=source_registry or seed_source_registry(),
    )


__all__ = ["EVENT_ENGINE_VERSION", "EventEngineFacade", "build_event_engine", "EventReasoningBatch", "EventReasoningEngine"]
