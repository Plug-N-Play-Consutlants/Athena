"""Doctor for Athena v0.5.5.3.0 Live Event Source Integration."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    CHECKS.append((name, bool(condition), detail))


def version_tuple(value: str) -> tuple[int, int, int, int, int]:
    try:
        parts = tuple(int(part) for part in str(value).split("."))
    except Exception:
        return (0, 0, 0, 0, 0)
    return parts if len(parts) == 5 else (0, 0, 0, 0, 0)


def main() -> int:
    from Core.version import ATHENA_VERSION, RELEASE_NAME, VERSION_SCHEMA
    from Knowledge.Events import (
        LIVE_EVENT_SOURCE_VERSION,
        LiveRssConnector,
        acquire_live_rss_sample,
        classify_rss_event_type,
        live_event_source_summary,
        parse_rss_items,
        sample_rss_payload,
        seed_live_connector_registry,
        seed_live_feed_registry,
        seed_live_source_registry,
    )
    from Engine.Events.facade import build_event_engine
    from Intelligence import reason_cross_sport_query

    check("version metadata", version_tuple(ATHENA_VERSION) >= (0, 5, 5, 3, 0), ATHENA_VERSION)
    check("release name", RELEASE_NAME in {"Live Event Source Integration", "Live Intelligence Consumption Engine", "Runtime Orchestration & Observability", "Scout Runtime Acceptance Hotfix", "Studio Log Visibility Hotfix", "Scout Runtime Continuation Hotfix", "Scout Session Logging Hotfix", "Scout Acceptance Communication Hotfix", "Public Analytical Routing Hotfix", "Response Composition Visibility Hotfix", "Acceptance Repository Cleanup and Pathway Audit", "Diagnostics Log Export Restoration"}, RELEASE_NAME)
    check("version schema", VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", VERSION_SCHEMA)
    check("live source version", LIVE_EVENT_SOURCE_VERSION == "0.5.5.3.0", LIVE_EVENT_SOURCE_VERSION)

    feeds = seed_live_feed_registry()
    check("live feed registry", {"rss_nhl_news", "rss_espn_nhl_news", "rss_multi_sport_news"}.issubset(set(feeds.feeds)), str(sorted(feeds.feeds)))
    check("live feed discover", any(feed.connector_type == "live_rss" for feed in feeds.by_sport("nhl", "nhl")), str([feed.feed_id for feed in feeds.by_sport("nhl", "nhl")]))

    sources = seed_live_source_registry()
    check("live source registry", len(sources.profiles) >= 3 and sources.by_sport("nhl", "nhl"), str(sources.to_dict()))

    connectors = seed_live_connector_registry()
    check("live connector registered", "live_rss" in connectors.available_types(), str(connectors.available_types()))
    check("connector type", LiveRssConnector().connector_type == "live_rss", LiveRssConnector().connector_type)

    rss_items = parse_rss_items(sample_rss_payload())
    check("rss parser", len(rss_items) == 2 and rss_items[0]["title"], str(rss_items))
    check("rss classifier injury", classify_rss_event_type("Player out with injury") == "injury", "injury")
    check("rss classifier trade", classify_rss_event_type("Club completed a trade") == "trade", "trade")

    sample = acquire_live_rss_sample()
    check("sample acquisition", sample.status == "success" and len(sample.events) == 2, str(sample.to_dict())[:500])
    check("sample normalized events", {event.event_type for event in sample.events} == {"injury", "trade"}, str([event.to_dict() for event in sample.events]))

    summary = live_event_source_summary()
    check("source summary", summary["network_safe_by_default"] is True and summary["live_rss_feed_count"] >= 3, str(summary))

    facade = build_event_engine()
    facade_summary = facade.summary()
    check("event facade exposes live sources", facade_summary.get("live_sources", {}).get("version") == "0.5.5.3.0", str(facade_summary.keys()))

    reasoning = reason_cross_sport_query("Summarize Blue Jays injuries")
    live_evidence = [item for item in reasoning.fused_evidence if item.source == "live_sources"]
    check("reasoning sees live source registry", len(live_evidence) >= 1, str(reasoning.to_dict()))

    print("Live Event Source Integration Doctor")
    print("=" * 64)
    failed = [row for row in CHECKS if not row[1]]
    for name, ok, detail in CHECKS:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"Overall status: {'PASS' if not failed else 'FAIL'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
