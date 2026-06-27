"""Validation for Athena v0.5.5.3.0 Live Event Source Integration."""
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
    from Core.version import ATHENA_VERSION, RELEASE_NAME
    import Knowledge.Events as events
    from Knowledge.Events.live_sources import (
        LIVE_EVENT_SOURCE_VERSION,
        LiveRssConnector,
        acquire_live_rss_events,
        acquire_live_rss_sample,
        live_event_source_summary,
        sample_rss_payload,
        seed_live_connector_registry,
        seed_live_feed_registry,
    )
    from Knowledge.Events.acquisition import FeedAcquisitionEngine
    from Engine.Events.facade import build_event_engine
    from Intelligence import reason_cross_sport_query

    check("version", version_tuple(ATHENA_VERSION) >= (0, 5, 5, 3, 0), ATHENA_VERSION)
    check("release name available", bool(RELEASE_NAME), RELEASE_NAME)
    check("package exports", all(hasattr(events, name) for name in ["LiveRssConnector", "live_event_source_summary", "acquire_live_rss_sample", "seed_live_feed_registry"]), "Knowledge.Events exports")
    check("live source version", LIVE_EVENT_SOURCE_VERSION == "0.5.5.3.0", LIVE_EVENT_SOURCE_VERSION)

    feeds = seed_live_feed_registry()
    connectors = seed_live_connector_registry({"rss_nhl_news": [{"xml": sample_rss_payload()}]})
    engine = FeedAcquisitionEngine(feeds, connectors)
    result = engine.acquire("rss_nhl_news")
    check("engine acquisition", result.status == "success" and result.raw_count == 1, str(result.to_dict())[:500])
    check("normalized event count", len(result.events) == 2, str([event.summary for event in result.events]))
    check("normalized confidence", all(0.4 <= event.confidence <= 1.0 for event in result.events), str([event.confidence for event in result.events]))
    check("normalized sources", all("trusted_newswire" in event.source_ids for event in result.events), str([event.source_ids for event in result.events]))

    direct = acquire_live_rss_sample()
    check("direct sample", direct.ok and len(direct.events) == 2, str(direct.to_dict())[:500])

    empty = acquire_live_rss_events("rss_nhl_news", payloads={}, allow_network=False)
    check("network safe default", empty.status in {"empty", "success"} and not empty.errors, str(empty.to_dict())[:300])
    check("live connector opt in flag", LiveRssConnector(allow_network=False).allow_network is False and LiveRssConnector(allow_network=True).allow_network is True, "opt-in network")

    summary = live_event_source_summary()
    check("summary contract", summary["network_safe_by_default"] is True and summary["sample_event_count"] == 2 and "live_rss" in summary["connector_types"], str(summary))

    facade = build_event_engine()
    check("facade live source method", facade.live_source_summary()["version"] == "0.5.5.3.0", str(facade.live_source_summary()))

    reasoning = reason_cross_sport_query("Summarize NHL injuries")
    payload = reasoning.to_dict()
    check("reasoning integration", any(item["source"] == "live_sources" for item in payload["fused_evidence"]), str(payload))

    # Prior sprint guardrail: cross-sport reasoning still returns a valid adapter/result.
    comparison = reason_cross_sport_query("Compare Auston Matthews vs Connor McDavid in the NHL")
    check("cross-sport guardrail", comparison.adapter == "Hockey Reasoning" and comparison.confidence > 0.4, str(comparison.to_dict()))

    failed = [row for row in CHECKS if not row[1]]
    print("Live Event Source Integration Validation")
    print("=" * 64)
    for name, ok, detail in CHECKS:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"Overall status: {'PASS' if not failed else 'FAIL'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
