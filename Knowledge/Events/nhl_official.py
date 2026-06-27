"""Official NHL feed connector profiles and deterministic normalization helpers.

The connector is network-safe by default: tests and Studio doctors validate the
contract using supplied/static payloads. Live HTTP acquisition can be enabled by
future connector implementations without changing the canonical output model.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from Knowledge.Events.acquisition import FeedResult, RestApiConnector, seed_connector_registry, FeedAcquisitionEngine
from Knowledge.Events.feeds import FeedDefinition, FeedRegistry, seed_feed_registry
from Knowledge.Events.models import EventRecord
from Knowledge.Events.normalizer import normalize_event_payload

NHL_OFFICIAL_CONNECTOR_VERSION = "0.5.2.1.1"

NHL_OFFICIAL_FEED_IDS = [
    "nhl_official_schedule",
    "nhl_official_standings",
    "nhl_official_club_stats",
]


class NhlOfficialApiConnector(RestApiConnector):
    connector_type = "nhl_official_api"

    def normalize(self, feed: FeedDefinition, raw_payload: Any) -> List[EventRecord]:
        items = raw_payload if isinstance(raw_payload, list) else [raw_payload]
        events: List[EventRecord] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            if feed.feed_id == "nhl_official_schedule":
                events.extend(_normalize_schedule_item(feed, item))
            elif feed.feed_id == "nhl_official_standings":
                events.append(_normalize_team_snapshot(feed, item, "standings"))
            elif feed.feed_id == "nhl_official_club_stats":
                events.append(_normalize_team_snapshot(feed, item, "club_stats"))
            else:
                events.append(normalize_event_payload({"source_id": feed.source_id, "sport": "nhl", **item}))
        return events


def _team_name(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("default") or value.get("name") or value.get("abbrev") or "Unknown Team")
    return str(value or "Unknown Team")


def _normalize_schedule_item(feed: FeedDefinition, item: Dict[str, Any]) -> List[EventRecord]:
    game_id = str(item.get("id") or item.get("gameId") or item.get("game_id") or "unknown_game")
    game_date = item.get("gameDate") or item.get("startTimeUTC") or item.get("date") or item.get("published_at")
    away = _team_name(item.get("awayTeam") or item.get("away"))
    home = _team_name(item.get("homeTeam") or item.get("home"))
    state = str(item.get("gameState") or item.get("state") or item.get("status") or "scheduled").lower()
    event_type = "game_result" if state in {"final", "off", "complete"} else "schedule_change"
    summary = f"{away} at {home} ({state})"
    payload = {
        "event_type": event_type,
        "sport": "nhl",
        "subject": f"{away} at {home}",
        "summary": summary,
        "occurred_at": game_date,
        "entities": [away, home],
        "entity_links": [
            {"entity_id": f"team_{away.lower().replace(' ', '_')}", "role": "away_team", "entity_type": "team", "confidence": 0.85},
            {"entity_id": f"team_{home.lower().replace(' ', '_')}", "role": "home_team", "entity_type": "team", "confidence": 0.85},
        ],
        "evidence": [{"source_id": feed.source_id, "title": f"Official NHL schedule game {game_id}", "observed_at": game_date or "", "confidence": 0.94}],
        "raw_game_id": game_id,
    }
    return [normalize_event_payload(payload)]


def _normalize_team_snapshot(feed: FeedDefinition, item: Dict[str, Any], snapshot_type: str) -> EventRecord:
    team = _team_name(item.get("teamName") or item.get("team") or item.get("teamAbbrev") or item.get("franchiseName"))
    date = item.get("date") or item.get("season") or item.get("published_at")
    payload = {
        "event_type": "event",
        "sport": "nhl",
        "subject": team,
        "summary": f"Official NHL {snapshot_type} snapshot for {team}.",
        "occurred_at": str(date) if date else None,
        "entities": [team],
        "entity_links": [{"entity_id": f"team_{team.lower().replace(' ', '_')}", "role": "subject", "entity_type": "team", "confidence": 0.8}],
        "evidence": [{"source_id": feed.source_id, "title": f"Official NHL {snapshot_type} payload", "observed_at": str(date or ""), "confidence": 0.92}],
        "snapshot_type": snapshot_type,
    }
    return normalize_event_payload(payload)


def seed_nhl_connector_registry(static_payloads: Optional[Dict[str, List[Dict[str, Any]]]] = None):
    registry = seed_connector_registry(static_payloads)
    registry.register("nhl_official_api", NhlOfficialApiConnector(static_payloads))
    return registry


def seed_nhl_feed_registry() -> FeedRegistry:
    return seed_feed_registry()


def acquire_nhl_official_sample(feed_id: str = "nhl_official_schedule", payloads: Optional[Dict[str, List[Dict[str, Any]]]] = None) -> FeedResult:
    sample_payloads = payloads or {
        "nhl_official_schedule": [
            {
                "id": 2026020001,
                "gameDate": "2026-10-08",
                "gameState": "scheduled",
                "awayTeam": {"default": "Toronto Maple Leafs"},
                "homeTeam": {"default": "Montreal Canadiens"},
            }
        ]
    }
    engine = FeedAcquisitionEngine(seed_nhl_feed_registry(), seed_nhl_connector_registry(sample_payloads))
    return engine.acquire(feed_id)


def nhl_connector_summary() -> Dict[str, Any]:
    feeds = seed_nhl_feed_registry()
    return {
        "version": NHL_OFFICIAL_CONNECTOR_VERSION,
        "official_feed_ids": list(NHL_OFFICIAL_FEED_IDS),
        "registered_nhl_feeds": [feed.feed_id for feed in feeds.by_sport("nhl", "nhl") if feed.connector_type == "nhl_official_api"],
        "connector_type": "nhl_official_api",
        "network_safe_by_default": True,
    }
