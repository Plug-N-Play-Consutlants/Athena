"""Live event source integration for Athena Event Intelligence.

This module adds network-capable but test-safe RSS ingestion. The default path is
read-only, deterministic and cache/static-payload friendly; callers must opt into
live network reads explicitly so doctors and validators never depend on internet
availability.
"""
from __future__ import annotations

import re
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from Knowledge.Events.acquisition import ConnectorRegistry, FeedAcquisitionEngine, FeedResult, RssFeedConnector, seed_connector_registry
from Knowledge.Events.feeds import FeedDefinition, FeedRegistry, RateLimitPolicy, RefreshPolicy, seed_feed_registry, utc_now_iso
from Knowledge.Events.models import EventRecord
from Knowledge.Events.normalizer import normalize_event_payload
from Knowledge.Events.source_intelligence import seed_source_registry

LIVE_EVENT_SOURCE_VERSION = "0.5.5.3.0"

DEFAULT_LIVE_RSS_FEEDS = [
    FeedDefinition(
        feed_id="rss_nhl_news",
        source_id="trusted_newswire",
        display_name="NHL News RSS",
        feed_type="rss_feed",
        sport="nhl",
        league="nhl",
        endpoint="https://www.nhl.com/rss/news.xml",
        connector_type="live_rss",
        auth_required=False,
        authority="trusted",
        supported_event_types=["news", "injury", "trade", "free_agent_signing", "contract_extension", "suspension"],
        refresh_policy=RefreshPolicy(mode="manual", interval_seconds=1800, priority=40, enabled=True),
        rate_limit=RateLimitPolicy(requests_per_minute=20, burst_limit=4, retry_backoff_seconds=60, max_retries=1),
        notes="RSS event evidence source. Network reads require explicit opt-in; validators use static payloads.",
    ),
    FeedDefinition(
        feed_id="rss_espn_nhl_news",
        source_id="trusted_newswire",
        display_name="ESPN NHL News RSS",
        feed_type="rss_feed",
        sport="nhl",
        league="nhl",
        endpoint="https://www.espn.com/espn/rss/nhl/news",
        connector_type="live_rss",
        auth_required=False,
        authority="trusted",
        supported_event_types=["news", "injury", "trade", "free_agent_signing", "contract_extension", "suspension"],
        refresh_policy=RefreshPolicy(mode="manual", interval_seconds=1800, priority=55, enabled=True),
        rate_limit=RateLimitPolicy(requests_per_minute=20, burst_limit=4, retry_backoff_seconds=60, max_retries=1),
        notes="Trusted RSS corroboration source. Network reads require explicit opt-in.",
    ),
    FeedDefinition(
        feed_id="rss_multi_sport_news",
        source_id="trusted_newswire",
        display_name="Multi-Sport News RSS",
        feed_type="rss_feed",
        sport="multi",
        league="multi",
        endpoint="",
        connector_type="live_rss",
        auth_required=False,
        authority="trusted",
        supported_event_types=["news", "injury", "transaction", "schedule_change"],
        refresh_policy=RefreshPolicy(mode="manual", interval_seconds=1800, priority=70, enabled=True),
        rate_limit=RateLimitPolicy(requests_per_minute=20, burst_limit=4, retry_backoff_seconds=60, max_retries=1),
        notes="Provider-neutral RSS slot for configured live source enrichment.",
    ),
]


@dataclass(frozen=True)
class LiveSourceProfile:
    feed_id: str
    source_id: str
    display_name: str
    sport: str
    league: str
    endpoint: str
    connector_type: str = "live_rss"
    network_enabled_by_default: bool = False
    confidence_role: str = "event_evidence"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feed_id": self.feed_id,
            "source_id": self.source_id,
            "display_name": self.display_name,
            "sport": self.sport,
            "league": self.league,
            "endpoint": self.endpoint,
            "connector_type": self.connector_type,
            "network_enabled_by_default": self.network_enabled_by_default,
            "confidence_role": self.confidence_role,
        }


@dataclass
class LiveSourceRegistry:
    profiles: Dict[str, LiveSourceProfile] = field(default_factory=dict)

    def register(self, profile: LiveSourceProfile) -> LiveSourceProfile:
        if not profile.feed_id:
            raise ValueError("feed_id is required")
        self.profiles[profile.feed_id] = profile
        return profile

    def get(self, feed_id: str) -> Optional[LiveSourceProfile]:
        return self.profiles.get(feed_id)

    def by_sport(self, sport: str = "multi", league: str | None = None) -> List[LiveSourceProfile]:
        sport_key = str(sport or "multi").lower()
        league_key = str(league or "").lower() if league else None
        result: List[LiveSourceProfile] = []
        for profile in self.profiles.values():
            if profile.sport.lower() not in {sport_key, "multi"}:
                continue
            if league_key and profile.league.lower() not in {league_key, "multi"}:
                continue
            result.append(profile)
        return sorted(result, key=lambda item: item.feed_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": LIVE_EVENT_SOURCE_VERSION,
            "profile_count": len(self.profiles),
            "network_enabled_by_default": False,
            "profiles": {key: value.to_dict() for key, value in sorted(self.profiles.items())},
        }


def _strip_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    return " ".join(text.split())


def _child_text(element: ET.Element, names: Iterable[str]) -> str:
    wanted = {name.lower() for name in names}
    for child in list(element):
        tag = child.tag.split("}")[-1].lower()
        if tag in wanted:
            return "".join(child.itertext()).strip()
    return ""


def parse_rss_items(raw_payload: Any) -> List[Dict[str, Any]]:
    """Parse RSS/Atom XML, or pass through list/dict payloads for tests."""
    if raw_payload is None:
        return []
    if isinstance(raw_payload, list):
        return [item for item in raw_payload if isinstance(item, dict)]
    if isinstance(raw_payload, dict):
        return [raw_payload]
    if isinstance(raw_payload, bytes):
        raw_text = raw_payload.decode("utf-8", errors="replace")
    else:
        raw_text = str(raw_payload or "")
    raw_text = raw_text.strip()
    if not raw_text:
        return []
    root = ET.fromstring(raw_text)
    candidates = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry") or root.findall(".//entry")
    items: List[Dict[str, Any]] = []
    for index, node in enumerate(candidates):
        title = _child_text(node, ["title"])
        link = _child_text(node, ["link"])
        if not link:
            for child in list(node):
                if child.tag.split("}")[-1].lower() == "link" and child.attrib.get("href"):
                    link = child.attrib.get("href", "")
                    break
        published = _child_text(node, ["pubDate", "published", "updated", "dc:date"])
        summary = _child_text(node, ["description", "summary", "content", "content:encoded"])
        guid = _child_text(node, ["guid", "id"]) or link or f"rss_item_{index}"
        items.append({
            "id": guid,
            "title": _strip_html(title),
            "summary": _strip_html(summary or title),
            "url": link,
            "published_at": published,
            "observed_at": utc_now_iso(),
            "raw_index": index,
        })
    return items


def classify_rss_event_type(title: str, summary: str = "") -> str:
    text = f"{title} {summary}".lower()
    rules = [
        ("injury", ("injury", "injured", "out", "day-to-day", "illness")),
        ("trade", ("trade", "traded", "acquire", "acquired")),
        ("free_agent_signing", ("sign", "signed", "signing", "free agent")),
        ("contract_extension", ("extension", "contract", "re-sign", "resign")),
        ("suspension", ("suspend", "suspended", "suspension")),
        ("schedule_change", ("postponed", "rescheduled", "schedule", "cancelled", "canceled")),
    ]
    for event_type, tokens in rules:
        if any(token in text for token in tokens):
            return event_type
    return "news"


class LiveRssConnector(RssFeedConnector):
    """RSS connector with explicit opt-in live HTTP support.

    By default this connector behaves deterministically using supplied payloads.
    Set ``allow_network=True`` to permit live reads from ``feed.endpoint``.
    """

    connector_type = "live_rss"

    def __init__(self, static_payloads: Optional[Dict[str, Any]] = None, *, allow_network: bool = False, timeout_seconds: int = 8) -> None:
        super().__init__(static_payloads or {})
        self.allow_network = bool(allow_network)
        self.timeout_seconds = int(timeout_seconds)

    def fetch(self, feed: Optional[FeedDefinition] = None) -> Any:
        if feed is None:
            return []
        if feed.feed_id in self.payloads:
            payload = self.payloads.get(feed.feed_id, [])
            if isinstance(payload, list) and len(payload) == 1 and isinstance(payload[0], dict) and "xml" in payload[0]:
                return payload[0].get("xml", "")
            return payload
        if not self.allow_network:
            return []
        if not feed.endpoint:
            return []
        request = urllib.request.Request(feed.endpoint, headers={"User-Agent": "AthenaEngine/0.5.5.3 RSS Event Connector"})
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310 - explicit opt-in read-only source acquisition
            return response.read()

    def normalize(self, feed: FeedDefinition, raw_payload: Any) -> List[EventRecord]:
        events: List[EventRecord] = []
        for item in parse_rss_items(raw_payload):
            title = str(item.get("title") or "Untitled RSS item")
            summary = str(item.get("summary") or title)
            event_type = classify_rss_event_type(title, summary)
            payload = {
                "event_type": event_type,
                "sport": feed.sport,
                "league": feed.league,
                "source_id": feed.source_id,
                "subject": item.get("subject") or title,
                "title": title,
                "summary": summary,
                "url": item.get("url", ""),
                "published_at": item.get("published_at") or item.get("observed_at") or utc_now_iso(),
                "evidence": [{
                    "source_id": feed.source_id,
                    "title": title,
                    "observed_at": item.get("published_at") or item.get("observed_at") or utc_now_iso(),
                    "url": item.get("url", ""),
                    "confidence": 0.72,
                    "excerpt": summary[:280],
                }],
                "raw_payload": item,
            }
            events.append(normalize_event_payload(payload))
        return events

    def health(self, feed: FeedDefinition):
        from Knowledge.Events.feeds import FeedHealth
        mode = "network-enabled" if self.allow_network else "static/cache-only"
        return FeedHealth(status="healthy" if self.connected else "warning", message=f"Live RSS connector available ({mode}).")


def seed_live_feed_registry() -> FeedRegistry:
    registry = seed_feed_registry()
    for feed in DEFAULT_LIVE_RSS_FEEDS:
        registry.register(feed)
    return registry


def seed_live_source_registry() -> LiveSourceRegistry:
    registry = LiveSourceRegistry()
    for feed in DEFAULT_LIVE_RSS_FEEDS:
        registry.register(LiveSourceProfile(
            feed_id=feed.feed_id,
            source_id=feed.source_id,
            display_name=feed.display_name,
            sport=feed.sport,
            league=feed.league,
            endpoint=feed.endpoint,
            connector_type=feed.connector_type,
        ))
    return registry


def seed_live_connector_registry(static_payloads: Optional[Dict[str, Any]] = None, *, allow_network: bool = False) -> ConnectorRegistry:
    registry = seed_connector_registry(static_payloads if isinstance(static_payloads, dict) else {})
    registry.register("live_rss", LiveRssConnector(static_payloads, allow_network=allow_network))
    return registry


def acquire_live_rss_events(feed_id: str = "rss_nhl_news", payloads: Optional[Dict[str, Any]] = None, *, allow_network: bool = False) -> FeedResult:
    engine = FeedAcquisitionEngine(seed_live_feed_registry(), seed_live_connector_registry(payloads, allow_network=allow_network))
    return engine.acquire(feed_id)


def sample_rss_payload() -> str:
    return """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<rss version=\"2.0\"><channel><title>Athena Test Feed</title>
<item><title>Maple Leafs forward day-to-day with injury</title><link>https://example.test/nhl/injury</link><pubDate>Tue, 23 Jun 2026 12:00:00 GMT</pubDate><description>Toronto forward is day-to-day after leaving practice.</description><guid>athena-rss-1</guid></item>
<item><title>Canadiens acquire defenseman in trade</title><link>https://example.test/nhl/trade</link><pubDate>Tue, 23 Jun 2026 13:00:00 GMT</pubDate><description>Montreal completed a roster transaction.</description><guid>athena-rss-2</guid></item>
</channel></rss>"""


def acquire_live_rss_sample() -> FeedResult:
    return acquire_live_rss_events("rss_nhl_news", {"rss_nhl_news": [{"xml": sample_rss_payload()}]}, allow_network=False)


def live_event_source_summary() -> Dict[str, Any]:
    feeds = seed_live_feed_registry()
    live_sources = seed_live_source_registry()
    source_registry = seed_source_registry()
    sample = acquire_live_rss_sample()
    return {
        "version": LIVE_EVENT_SOURCE_VERSION,
        "network_safe_by_default": True,
        "live_network_opt_in_required": True,
        "feed_count": len(feeds.feeds),
        "live_rss_feed_count": len([feed for feed in feeds.feeds.values() if feed.connector_type == "live_rss"]),
        "connector_types": seed_live_connector_registry().available_types(),
        "source_profile_count": len(source_registry.sources),
        "live_source_registry": live_sources.to_dict(),
        "sample_status": sample.status,
        "sample_event_count": len(sample.events),
        "sample_event_types": sorted({event.event_type for event in sample.events}),
        "feeds": [profile.to_dict() for profile in live_sources.profiles.values()],
    }


__all__ = [
    "LIVE_EVENT_SOURCE_VERSION",
    "LiveSourceProfile",
    "LiveSourceRegistry",
    "LiveRssConnector",
    "parse_rss_items",
    "classify_rss_event_type",
    "seed_live_feed_registry",
    "seed_live_source_registry",
    "seed_live_connector_registry",
    "acquire_live_rss_events",
    "acquire_live_rss_sample",
    "live_event_source_summary",
    "sample_rss_payload",
]
