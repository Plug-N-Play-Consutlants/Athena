"""Feed Registry and health models for Athena Event Intelligence.

Feeds describe where event evidence may be acquired. They are Knowledge-layer
configuration objects; fetching and reasoning stay outside this module.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

FEED_REGISTRY_VERSION = "0.5.1.4.0"

FEED_TYPES = [
    "official_api",
    "official_feed",
    "rss_feed",
    "json_feed",
    "newswire",
    "provider_feed",
    "static_file",
]

HEALTH_STATES = ["healthy", "warning", "offline", "disabled", "unknown"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class RateLimitPolicy:
    requests_per_minute: int = 60
    burst_limit: int = 10
    retry_backoff_seconds: int = 30
    max_retries: int = 2

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RefreshPolicy:
    mode: str = "manual"
    interval_seconds: int = 3600
    priority: int = 50
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FeedHealth:
    status: str = "unknown"
    last_attempted_at: Optional[str] = None
    last_success_at: Optional[str] = None
    consecutive_failures: int = 0
    average_response_ms: float = 0.0
    message: str = ""

    def mark_attempt(self, timestamp: Optional[str] = None) -> None:
        self.last_attempted_at = timestamp or utc_now_iso()

    def mark_success(self, response_ms: float = 0.0, timestamp: Optional[str] = None) -> None:
        now = timestamp or utc_now_iso()
        self.last_attempted_at = now
        self.last_success_at = now
        self.consecutive_failures = 0
        self.status = "healthy"
        self.message = "Last acquisition succeeded."
        if response_ms >= 0:
            if self.average_response_ms <= 0:
                self.average_response_ms = float(response_ms)
            else:
                self.average_response_ms = round((self.average_response_ms * 0.7) + (float(response_ms) * 0.3), 2)

    def mark_failure(self, message: str = "", timestamp: Optional[str] = None) -> None:
        self.last_attempted_at = timestamp or utc_now_iso()
        self.consecutive_failures += 1
        self.status = "offline" if self.consecutive_failures >= 3 else "warning"
        self.message = message or "Acquisition failed."

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FeedDefinition:
    feed_id: str
    source_id: str
    display_name: str
    feed_type: str
    sport: str = "multi"
    league: str = "multi"
    endpoint: str = ""
    connector_type: str = "static_file"
    auth_required: bool = False
    authority: str = "trusted"
    supported_event_types: List[str] = field(default_factory=list)
    refresh_policy: RefreshPolicy = field(default_factory=RefreshPolicy)
    rate_limit: RateLimitPolicy = field(default_factory=RateLimitPolicy)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["refresh_policy"] = self.refresh_policy.to_dict()
        data["rate_limit"] = self.rate_limit.to_dict()
        return data


@dataclass
class FeedRegistry:
    feeds: Dict[str, FeedDefinition] = field(default_factory=dict)
    health: Dict[str, FeedHealth] = field(default_factory=dict)

    def register(self, feed: FeedDefinition) -> FeedDefinition:
        if not feed.feed_id:
            raise ValueError("feed_id is required")
        if feed.feed_type not in FEED_TYPES:
            raise ValueError(f"Unsupported feed_type: {feed.feed_type}")
        self.feeds[feed.feed_id] = feed
        self.health.setdefault(feed.feed_id, FeedHealth(status="disabled" if not feed.refresh_policy.enabled else "unknown"))
        return feed

    def get(self, feed_id: str) -> Optional[FeedDefinition]:
        return self.feeds.get(feed_id)

    def health_for(self, feed_id: str) -> FeedHealth:
        self.health.setdefault(feed_id, FeedHealth())
        return self.health[feed_id]

    def active_feeds(self) -> List[FeedDefinition]:
        return [feed for feed in self.feeds.values() if feed.refresh_policy.enabled]

    def by_sport(self, sport: str, league: str | None = None) -> List[FeedDefinition]:
        sport_key = str(sport or "").lower()
        league_key = str(league or "").lower() if league else None
        result = []
        for feed in self.active_feeds():
            if feed.sport.lower() not in {sport_key, "multi"}:
                continue
            if league_key and feed.league.lower() not in {league_key, "multi"}:
                continue
            result.append(feed)
        return sorted(result, key=lambda feed: (feed.refresh_policy.priority, feed.feed_id))

    def by_connector(self, connector_type: str) -> List[FeedDefinition]:
        return [feed for feed in self.active_feeds() if feed.connector_type == connector_type]

    def discover(self, sport: str = "multi", league: str | None = None, event_type: str | None = None, include_unhealthy: bool = False) -> List[FeedDefinition]:
        """Compatibility method for older Event Intelligence validators."""
        return discover_feeds(self, sport=sport, league=league, event_type=event_type, include_unhealthy=include_unhealthy)

    def summarize(self) -> Dict[str, Any]:
        active = self.active_feeds()
        return {
            "version": FEED_REGISTRY_VERSION,
            "feed_count": len(self.feeds),
            "active_feed_count": len(active),
            "feed_types": sorted({feed.feed_type for feed in self.feeds.values()}),
            "connector_types": sorted({feed.connector_type for feed in self.feeds.values()}),
            "healthy_count": sum(1 for item in self.health.values() if item.status == "healthy"),
            "warning_count": sum(1 for item in self.health.values() if item.status == "warning"),
            "offline_count": sum(1 for item in self.health.values() if item.status == "offline"),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": FEED_REGISTRY_VERSION,
            "feeds": {key: value.to_dict() for key, value in sorted(self.feeds.items())},
            "health": {key: value.to_dict() for key, value in sorted(self.health.items())},
            "summary": self.summarize(),
        }


def discover_feeds(registry: FeedRegistry, sport: str = "multi", league: str | None = None, event_type: str | None = None, include_unhealthy: bool = False) -> List[FeedDefinition]:
    candidates = registry.by_sport(sport, league)
    if event_type:
        event_key = str(event_type).strip().lower()
        candidates = [feed for feed in candidates if not feed.supported_event_types or event_key in set(feed.supported_event_types)]
    if not include_unhealthy:
        candidates = [feed for feed in candidates if registry.health_for(feed.feed_id).status not in {"offline", "disabled"}]
    return sorted(candidates, key=lambda feed: (feed.authority != "official", feed.refresh_policy.priority, feed.feed_id))


def seed_feed_registry() -> FeedRegistry:
    registry = FeedRegistry()
    registry.register(FeedDefinition(
        feed_id="nhl_official_schedule",
        source_id="nhl_api",
        display_name="NHL Official Schedule API",
        feed_type="official_api",
        sport="nhl",
        league="nhl",
        endpoint="https://api-web.nhle.com/v1/schedule/now",
        connector_type="nhl_official_api",
        auth_required=False,
        authority="official",
        supported_event_types=["schedule_change", "game_result"],
        refresh_policy=RefreshPolicy(mode="scheduled", interval_seconds=1800, priority=10),
        rate_limit=RateLimitPolicy(requests_per_minute=120, burst_limit=20, retry_backoff_seconds=20, max_retries=2),
        notes="Official schedule and score source used as the first NHL connector target.",
    ))
    registry.register(FeedDefinition(
        feed_id="nhl_official_standings",
        source_id="nhl_api",
        display_name="NHL Official Standings API",
        feed_type="official_api",
        sport="nhl",
        league="nhl",
        endpoint="https://api-web.nhle.com/v1/standings/now",
        connector_type="nhl_official_api",
        auth_required=False,
        authority="official",
        supported_event_types=["team_snapshot"],
        refresh_policy=RefreshPolicy(mode="scheduled", interval_seconds=21600, priority=20),
        rate_limit=RateLimitPolicy(requests_per_minute=60, burst_limit=10, retry_backoff_seconds=30, max_retries=2),
        notes="Official standings source for team context events.",
    ))
    registry.register(FeedDefinition(
        feed_id="nhl_official_club_stats",
        source_id="nhl_api",
        display_name="NHL Official Club Stats API",
        feed_type="official_api",
        sport="nhl",
        league="nhl",
        endpoint="https://api.nhle.com/stats/rest/en/team/summary",
        connector_type="nhl_official_api",
        auth_required=False,
        authority="official",
        supported_event_types=["team_snapshot"],
        refresh_policy=RefreshPolicy(mode="manual", interval_seconds=86400, priority=30),
        rate_limit=RateLimitPolicy(requests_per_minute=60, burst_limit=10, retry_backoff_seconds=30, max_retries=2),
        notes="Official NHL stats API profile; live use remains connector-gated.",
    ))
    registry.register(FeedDefinition(
        feed_id="trusted_nhl_newswire",
        source_id="trusted_newswire",
        display_name="Trusted NHL Newswire Feed",
        feed_type="newswire",
        sport="nhl",
        league="nhl",
        endpoint="",
        connector_type="rss",
        auth_required=False,
        authority="trusted",
        supported_event_types=["trade", "injury", "free_agent_signing", "contract_extension", "suspension"],
        refresh_policy=RefreshPolicy(mode="manual", interval_seconds=1800, priority=50, enabled=True),
        notes="Structured placeholder for AP/Reuters-style feed integration.",
    ))
    return registry
