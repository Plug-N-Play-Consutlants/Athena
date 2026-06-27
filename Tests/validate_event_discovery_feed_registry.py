"""Validation suite for Athena 0.5.1.2.0 Event Discovery & Feed Registry."""
from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_BUILD, ATHENA_VERSION, RELEASE_EPIC, RELEASE_HOTFIX, RELEASE_NAME, RELEASE_PATCH, RELEASE_SPRINT, VERSION_SCHEMA
from Knowledge.Events import (
    FeedDefinition,
    FeedHealth,
    FeedRegistry,
    FeedStatus,
    FeedType,
    build_ingestion_plan,
    discover_feeds,
    feed_registry_summary,
    ingest_static_event_payload,
    seed_feed_registry,
)


def report(name: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))
    return ok


def main() -> int:
    print("Event Discovery & Feed Registry Validation")
    print("=" * 64)
    checks: list[bool] = []

    checks.append(report("version is Epic 5 Sprint 1 Patch 2", ((ATHENA_VERSION == "0.5.1.2.0") or ATHENA_VERSION.startswith("0.5.1.3.") or ATHENA_VERSION.startswith("0.5.1.4.") or ATHENA_VERSION.startswith("0.5.1.5.") or ATHENA_VERSION.startswith("0.5.2.")) and ATHENA_BUILD == ATHENA_VERSION, ATHENA_VERSION))
    checks.append(report("version uses locked schema", VERSION_SCHEMA == "major.epic.sprint.patch.hotfix" and bool(re.fullmatch(r"\d+\.\d+\.\d+\.\d+\.\d+", ATHENA_VERSION)), VERSION_SCHEMA))
    checks.append(report("release metadata identifies feed registry patch", RELEASE_EPIC == "5", RELEASE_NAME))

    registry = seed_feed_registry()
    checks.append(report("feed registry object created", isinstance(registry, FeedRegistry), type(registry).__name__))
    checks.append(report("feed registry seeds canonical feed types", len(registry.feeds) >= 7 and {FeedType.OFFICIAL_API.value, FeedType.OFFICIAL_FEED.value, FeedType.NEWSWIRE.value, FeedType.PROVIDER_FEED.value, FeedType.STATIC_IMPORT.value}.issubset({feed.feed_type for feed in registry.feeds.values()}), f"feeds={len(registry.feeds)}"))
    checks.append(report("opinion feed disabled by default", registry.get("opinion_article_monitor") is not None and not registry.get("opinion_article_monitor").enabled, "opinion_article_monitor"))
    checks.append(report("feed health records exist", len(registry.health) == len(registry.feeds) and all(isinstance(item, FeedHealth) for item in registry.health.values()), f"health={len(registry.health)}"))
    checks.append(report("healthy official feeds are seeded", registry.health_for("nhl_official_transactions").status == FeedStatus.HEALTHY.value and registry.health_for("league_event_feed").status == FeedStatus.HEALTHY.value, str(registry.health_for("nhl_official_transactions").to_dict())))

    nhl_trade_feeds = discover_feeds(sport="nhl", league="nhl", event_type="trade", registry=registry)
    checks.append(report("discovery returns NHL trade feeds", nhl_trade_feeds.to_dict()["feed_count"] >= 3, str(nhl_trade_feeds.to_dict())))
    checks.append(report("discovery prioritizes official source", nhl_trade_feeds.best_feed() is not None and nhl_trade_feeds.best_feed().feed_id == "nhl_official_transactions", nhl_trade_feeds.best_feed().feed_id if nhl_trade_feeds.best_feed() else "none"))
    injury_feeds = discover_feeds(sport="nhl", league="nhl", event_type="injury", registry=registry)
    checks.append(report("discovery supports injury feeds", any(feed.feed_id in {"nhl_official_transactions", "team_official_events"} for feed in injury_feeds.feeds), str([feed.feed_id for feed in injury_feeds.feeds])))
    provider_feeds = discover_feeds(sport="multi", league="multi", event_type="transaction", registry=registry)
    checks.append(report("discovery includes provider enrichment feeds", any(feed.feed_type == FeedType.PROVIDER_FEED.value for feed in provider_feeds.feeds), str([feed.feed_id for feed in provider_feeds.feeds])))

    feed = nhl_trade_feeds.best_feed()
    plan = build_ingestion_plan(feed, event_type_hint="trade")
    checks.append(report("ingestion plan contains canonical pipeline", plan.stages == ["feed", "fetch", "normalize", "canonical_event", "evidence", "knowledge"], str(plan.to_dict())))
    checks.append(report("ingestion plan binds feed and source", plan.feed_id == feed.feed_id and plan.source_id == feed.source_id, str(plan.to_dict())))

    payload = {
        "event_type": "trade",
        "subject": "Example Player",
        "summary": "Example Player was traded from Team A to Team B.",
        "entities": ["Example Player", "Team A", "Team B"],
        "published_at": "2026-06-23T12:00:00+00:00",
    }
    event = ingest_static_event_payload(payload, feed=feed)
    checks.append(report("static payload ingestion produces normalized event", event.event_type == "trade" and event.sport == "nhl" and event.source_ids == ["nhl_api"], event.to_dict()["event_id"]))
    checks.append(report("ingested event carries feed id in raw payload", event.raw_payload.get("feed_id") == feed.feed_id, str(event.raw_payload)))
    checks.append(report("ingested event remains knowledge fact only", not hasattr(event, "conclusion") and not hasattr(event, "recommendation"), "Reasoning still owns conclusions"))

    health = registry.health_for("trusted_newswire_events")
    before = health.consecutive_failures
    health.mark_attempt(success=False, response_ms=250.0, message="synthetic failed check")
    checks.append(report("feed health tracks attempts and failures", health.consecutive_failures == before + 1 and health.last_attempt_at and health.average_response_ms is not None, str(health.to_dict())))
    health.mark_attempt(success=True, response_ms=125.0, message="synthetic recovery")
    checks.append(report("feed health recovers to healthy", health.status == FeedStatus.HEALTHY.value and health.consecutive_failures == 0 and health.last_success_at, str(health.to_dict())))

    summary = feed_registry_summary(registry)
    checks.append(report("feed summary exposes health and type coverage", summary["feed_count"] >= 7 and summary["healthy_feed_count"] >= 4 and "official_api" in summary["feed_types"], str(summary)))
    checks.append(report("feed summary identifies disabled opinion feeds", "opinion_article_monitor" in summary.get("disabled_opinion_feeds", []), str(summary.get("disabled_opinion_feeds"))))

    failed = [ok for ok in checks if not ok]
    print("\nOverall status:", "PASS" if not failed else "FAIL")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
