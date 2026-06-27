"""Event acquisition contracts and deterministic connector runtime."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Dict, Iterable, List, Optional, Protocol

from Knowledge.Events.feeds import FeedDefinition, FeedHealth, FeedRegistry, seed_feed_registry, utc_now_iso
from Knowledge.Events.models import EventRecord
from Knowledge.Events.normalizer import normalize_event_payload

EVENT_ACQUISITION_VERSION = "0.5.1.4.0"


@dataclass(frozen=True)
class FeedResult:
    status: str
    source_id: str
    feed_id: str
    events: List[EventRecord] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=utc_now_iso)
    raw_count: int = 0

    @property
    def ok(self) -> bool:
        return self.status in {"success", "partial"} and not self.errors

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["events"] = [event.to_dict() for event in self.events]
        data["ok"] = self.ok
        return data


class EventConnector(Protocol):
    connector_type: str

    def connect(self) -> bool: ...
    def fetch(self, feed: FeedDefinition) -> Any: ...
    def normalize(self, feed: FeedDefinition, raw_payload: Any) -> List[EventRecord]: ...
    def health(self, feed: FeedDefinition) -> FeedHealth: ...
    def disconnect(self) -> None: ...


class StaticPayloadConnector:
    connector_type = "static_file"

    def __init__(self, *args: Any, payloads: Optional[Dict[str, List[Dict[str, Any]]]] = None) -> None:
        """Create a static connector.

        Supports both the newer registry form::

            StaticPayloadConnector({"feed_id": [payload, ...]})

        and the older Event Intelligence compatibility form::

            StaticPayloadConnector("source_id", "feed_id", [payload, ...])

        The older form is still used by cross-domain/event validators and must
        remain import-safe for downstream Event packages.
        """
        self.connected = False
        self.default_source_id = "unknown"
        self.default_feed_id = "static_payload"
        self.payloads: Dict[str, List[Dict[str, Any]]] = {}

        if payloads is not None:
            self.payloads = dict(payloads)
        elif len(args) == 1 and isinstance(args[0], dict):
            self.payloads = dict(args[0])
        elif len(args) >= 3 and isinstance(args[0], str) and isinstance(args[1], str):
            self.default_source_id = args[0]
            self.default_feed_id = args[1]
            raw_items = args[2]
            if isinstance(raw_items, list):
                self.payloads = {self.default_feed_id: [item for item in raw_items if isinstance(item, dict)]}
            elif isinstance(raw_items, dict):
                self.payloads = {self.default_feed_id: [raw_items]}
            else:
                self.payloads = {self.default_feed_id: []}
        elif len(args) == 0:
            self.payloads = {}
        else:
            raise TypeError("StaticPayloadConnector expects a payload map or source_id, feed_id, payloads")

    def connect(self) -> bool:
        self.connected = True
        return True

    def fetch(self, feed: Optional[FeedDefinition] = None) -> List[Dict[str, Any]]:
        feed_id = feed.feed_id if feed is not None else self.default_feed_id
        return list(self.payloads.get(feed_id, []))

    def normalize(self, feed: FeedDefinition, raw_payload: Any) -> List[EventRecord]:
        events: List[EventRecord] = []
        items = raw_payload if isinstance(raw_payload, list) else [raw_payload]
        for item in items:
            if not isinstance(item, dict):
                continue
            enriched = {
                "source_id": feed.source_id,
                "sport": feed.sport,
                "event_type": (feed.supported_event_types[0] if feed.supported_event_types else "event"),
                **item,
            }
            events.append(normalize_event_payload(enriched))
        return events

    def health(self, feed: FeedDefinition) -> FeedHealth:
        status = "healthy" if self.connected else "warning"
        return FeedHealth(status=status, message="Static connector available." if self.connected else "Static connector not connected.")

    def disconnect(self) -> None:
        self.connected = False


class JsonFeedConnector(StaticPayloadConnector):
    connector_type = "json_feed"


class RssFeedConnector(StaticPayloadConnector):
    connector_type = "rss"


class ProviderAdapterConnector(StaticPayloadConnector):
    connector_type = "provider_adapter"


class RestApiConnector(StaticPayloadConnector):
    connector_type = "rest_api"


@dataclass
class ConnectorRegistry:
    connectors: Dict[str, EventConnector] = field(default_factory=dict)

    def register(self, connector_type: str, connector: EventConnector) -> EventConnector:
        self.connectors[connector_type] = connector
        return connector

    def get(self, connector_type: str) -> Optional[EventConnector]:
        return self.connectors.get(connector_type)

    def available_types(self) -> List[str]:
        return sorted(self.connectors)


def seed_connector_registry(static_payloads: Optional[Dict[str, List[Dict[str, Any]]]] = None) -> ConnectorRegistry:
    registry = ConnectorRegistry()
    payload_map = static_payloads if isinstance(static_payloads, dict) else {}
    registry.register("static_file", StaticPayloadConnector(payload_map))
    registry.register("json_feed", JsonFeedConnector(payload_map))
    registry.register("rss", RssFeedConnector(payload_map))
    registry.register("provider_adapter", ProviderAdapterConnector(payload_map))
    registry.register("rest_api", RestApiConnector(payload_map))
    return registry


class FeedAcquisitionEngine:
    def __init__(self, feed_registry: Optional[FeedRegistry] = None, connector_registry: Optional[ConnectorRegistry] = None) -> None:
        self.feed_registry = feed_registry or seed_feed_registry()
        self.connector_registry = connector_registry or seed_connector_registry()

    def acquire(self, feed_id: str) -> FeedResult:
        feed = self.feed_registry.get(feed_id)
        if not feed:
            return FeedResult(status="error", source_id="unknown", feed_id=feed_id, errors=[f"Unknown feed: {feed_id}"])
        connector = self.connector_registry.get(feed.connector_type) or self.connector_registry.get("static_file")
        if not connector:
            return FeedResult(status="error", source_id=feed.source_id, feed_id=feed.feed_id, errors=[f"No connector registered for {feed.connector_type}"])
        started = perf_counter()
        health = self.feed_registry.health_for(feed.feed_id)
        health.mark_attempt()
        try:
            connector.connect()
            raw = connector.fetch(feed)
            events = connector.normalize(feed, raw)
            duration = round((perf_counter() - started) * 1000, 2)
            health.mark_success(duration)
            raw_count = len(raw) if isinstance(raw, list) else (1 if raw else 0)
            status = "success" if events else "empty"
            warnings = [] if events else ["Feed returned no normalized events."]
            return FeedResult(status=status, source_id=feed.source_id, feed_id=feed.feed_id, events=events, warnings=warnings, duration_ms=duration, raw_count=raw_count)
        except Exception as exc:
            duration = round((perf_counter() - started) * 1000, 2)
            health.mark_failure(str(exc))
            return FeedResult(status="error", source_id=feed.source_id, feed_id=feed.feed_id, errors=[str(exc)], duration_ms=duration)
        finally:
            try:
                connector.disconnect()
            except Exception:
                pass

    def acquire_many(self, feed_ids: Iterable[str]) -> List[FeedResult]:
        return [self.acquire(feed_id) for feed_id in feed_ids]


def acquire_events(connector: EventConnector, feed: Optional[FeedDefinition] = None) -> FeedResult:
    """Compatibility helper for older Event Intelligence callers.

    Earlier Epic 5 validators pass a connector instance directly and expect a
    FeedResult. Newer code should prefer FeedAcquisitionEngine, but this helper
    preserves the public Knowledge.Events contract.
    """
    if feed is None:
        feed = FeedDefinition(
            feed_id=getattr(connector, "default_feed_id", "static_payload"),
            source_id=getattr(connector, "default_source_id", "unknown"),
            display_name="Static Payload Compatibility Feed",
            feed_type="static_file",
            sport="multi",
            league="multi",
            connector_type=getattr(connector, "connector_type", "static_file"),
            supported_event_types=[],
        )
    started = perf_counter()
    try:
        connector.connect()
        raw = connector.fetch(feed)
        events = connector.normalize(feed, raw)
        duration = round((perf_counter() - started) * 1000, 2)
        raw_count = len(raw) if isinstance(raw, list) else (1 if raw else 0)
        status = "success" if events else "empty"
        warnings = [] if events else ["Feed returned no normalized events."]
        return FeedResult(
            status=status,
            source_id=feed.source_id,
            feed_id=feed.feed_id,
            events=events,
            warnings=warnings,
            duration_ms=duration,
            raw_count=raw_count,
        )
    except Exception as exc:
        duration = round((perf_counter() - started) * 1000, 2)
        return FeedResult(
            status="error",
            source_id=getattr(feed, "source_id", "unknown"),
            feed_id=getattr(feed, "feed_id", "unknown"),
            errors=[str(exc)],
            duration_ms=duration,
        )
    finally:
        try:
            connector.disconnect()
        except Exception:
            pass
