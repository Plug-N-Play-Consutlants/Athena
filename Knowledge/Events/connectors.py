"""Connector abstractions for Event Acquisition.

Connectors are deterministic adapters at the Fetch/Build boundary. They return a
common FeedResult so Knowledge and Reasoning do not need connector-specific code.
Network-enabled connectors are intentionally inert in this release; live polling
arrives in a later connector-specific patch.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from Knowledge.Events.feeds import FeedProfile, FeedStatus, utc_now_iso
from Knowledge.Events.models import EventRecord
from Knowledge.Events.normalizer import normalize_event_payload

CONNECTOR_VERSION = "0.5.1.3.0"


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

    def ok(self) -> bool:
        return self.status == FeedStatus.HEALTHY.value and not self.errors

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["events"] = [event.to_dict() for event in self.events]
        return data


class BaseFeedConnector:
    connector_type = "base"

    def __init__(self, feed: FeedProfile) -> None:
        self.feed = feed
        self.connected = False

    def connect(self) -> bool:
        self.connected = True
        return self.connected

    def fetch(self) -> Any:
        raise NotImplementedError

    def normalize(self, payload: Any) -> List[EventRecord]:
        if payload is None:
            return []
        if isinstance(payload, dict) and isinstance(payload.get("events"), list):
            raw_events = payload["events"]
        elif isinstance(payload, list):
            raw_events = payload
        elif isinstance(payload, dict):
            raw_events = [payload]
        else:
            raw_events = []
        events: List[EventRecord] = []
        for item in raw_events:
            if isinstance(item, EventRecord):
                events.append(item)
            elif isinstance(item, dict):
                events.append(normalize_event_payload({"source_id": self.feed.source_id, "sport": self.feed.sport, **item}))
        return events

    def health(self) -> Dict[str, Any]:
        return {"connector_type": self.connector_type, "connected": self.connected, "feed_id": self.feed.feed_id}

    def disconnect(self) -> None:
        self.connected = False

    def run(self) -> FeedResult:
        started = time.perf_counter()
        warnings: List[str] = []
        errors: List[str] = []
        events: List[EventRecord] = []
        raw_count = 0
        try:
            self.connect()
            payload = self.fetch()
            if isinstance(payload, dict) and isinstance(payload.get("events"), list):
                raw_count = len(payload["events"])
            elif isinstance(payload, list):
                raw_count = len(payload)
            elif payload is not None:
                raw_count = 1
            events = self.normalize(payload)
            status = FeedStatus.HEALTHY.value
        except Exception as exc:
            status = FeedStatus.OFFLINE.value
            errors.append(str(exc))
        finally:
            self.disconnect()
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        if not events and not errors:
            warnings.append("feed returned no canonical events")
        return FeedResult(status=status, source_id=self.feed.source_id, feed_id=self.feed.feed_id, events=events, warnings=warnings, errors=errors, duration_ms=duration_ms, raw_count=raw_count)


class StaticPayloadConnector(BaseFeedConnector):
    connector_type = "static_file"

    def __init__(self, feed: FeedProfile, payload: Any | None = None, path: str | Path | None = None) -> None:
        super().__init__(feed)
        self.payload = payload
        self.path = Path(path) if path else None

    def fetch(self) -> Any:
        if self.payload is not None:
            return self.payload
        if self.path:
            text = self.path.read_text(encoding="utf-8")
            return json.loads(text)
        return {"events": []}


class JsonFeedConnector(StaticPayloadConnector):
    connector_type = "json_feed"


class RssFeedConnector(BaseFeedConnector):
    connector_type = "rss"

    def fetch(self) -> Any:
        return {"events": [], "note": "RSS network fetch is disabled until official connector patch."}


class RestApiConnector(BaseFeedConnector):
    connector_type = "rest_api"

    def fetch(self) -> Any:
        return {"events": [], "note": "REST network fetch is disabled until official connector patch."}


class ProviderAdapterConnector(BaseFeedConnector):
    connector_type = "provider_adapter"

    def fetch(self) -> Any:
        return {"events": [], "note": "Provider adapter event acquisition is disabled until provider-specific patch."}


CONNECTOR_CLASSES = {
    "static_file": StaticPayloadConnector,
    "json_feed": JsonFeedConnector,
    "rss": RssFeedConnector,
    "rest_api": RestApiConnector,
    "provider_adapter": ProviderAdapterConnector,
}


def connector_for(feed: FeedProfile, payload: Any | None = None) -> BaseFeedConnector:
    cls = CONNECTOR_CLASSES.get(feed.connector_type, StaticPayloadConnector)
    if issubclass(cls, StaticPayloadConnector):
        return cls(feed, payload=payload)
    return cls(feed)


def connector_registry_summary() -> Dict[str, Any]:
    return {"version": CONNECTOR_VERSION, "connector_types": sorted(CONNECTOR_CLASSES), "network_fetch_enabled": False}
