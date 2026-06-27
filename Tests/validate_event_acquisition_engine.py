"""Validation suite for Athena 0.5.1.3.0 Event Acquisition Engine."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.version import ATHENA_VERSION, ATHENA_BUILD, RELEASE_PATCH, RELEASE_HOTFIX, VERSION_SCHEMA
from Knowledge.Events.acquisition import EventAcquisitionEngine, FeedScheduler, demo_static_payload
from Knowledge.Events.connectors import FeedResult, connector_registry_summary
from Knowledge.Events.feeds import FeedStatus, FeedType, RefreshPolicy, seed_feed_registry


def report(name: str, ok: bool, detail: str = "") -> tuple[str, bool, str]:
    return (name, bool(ok), detail)


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    checks.append(report("version is 0.5.1.3.0", ((ATHENA_VERSION == "0.5.1.3.0") or ATHENA_VERSION.startswith("0.5.1.4.") or ATHENA_VERSION.startswith("0.5.1.5.") or ATHENA_VERSION.startswith("0.5.2.")) and ATHENA_BUILD == ATHENA_VERSION and VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", ATHENA_VERSION))

    registry = seed_feed_registry()
    all_feeds = registry.all()
    checks.append(report("feed registry seeds multiple feeds", len(all_feeds) >= 6, str(registry.health_summary())))
    checks.append(report("official NHL feeds discover first", registry.discover(sport="nhl", league="nhl")[0].source_id == "nhl_api", registry.discover(sport="nhl", league="nhl")[0].to_dict()))
    feed_types = {feed.feed_type for feed in all_feeds}
    checks.append(report("registry includes official api/rss/provider/static coverage", {FeedType.OFFICIAL_API.value, FeedType.NEWSWIRE.value, FeedType.PROVIDER_ADAPTER.value, FeedType.STATIC_FILE.value}.issubset(feed_types), str(sorted(feed_types))))
    checks.append(report("feed health summary includes available count", registry.health_summary().get("available_count", 0) == len(registry.available()), str(registry.health_summary())))

    connectors = connector_registry_summary()
    checks.append(report("connector registry includes five connector types", {"rss", "rest_api", "json_feed", "static_file", "provider_adapter"}.issubset(set(connectors.get("connector_types", []))), str(connectors)))
    checks.append(report("network fetch remains disabled in foundation", connectors.get("network_fetch_enabled") is False, str(connectors)))

    scheduler = FeedScheduler(registry)
    manual = scheduler.plan_manual(["static_event_import", "missing"])
    ondemand = scheduler.plan_on_demand(sport="nhl", league="nhl")
    scheduled = scheduler.plan_scheduled()
    checks.append(report("manual scheduler filters unknown feeds", manual.feed_ids == ["static_event_import"] and manual.mode == RefreshPolicy.MANUAL.value, str(manual.to_dict())))
    checks.append(report("on-demand scheduler returns compatible feeds", "nhl_official_transactions" in ondemand.feed_ids, str(ondemand.to_dict())))
    checks.append(report("scheduled scheduler is explicit and non-background", scheduled.scheduled is True and scheduled.background_enabled is False, str(scheduled.to_dict())))

    engine = EventAcquisitionEngine(registry)
    result = engine.run_feed("static_event_import", payload=demo_static_payload())
    checks.append(report("static payload acquisition returns FeedResult", isinstance(result, FeedResult), type(result).__name__))
    checks.append(report("canonical feed result is healthy", result.status == FeedStatus.HEALTHY.value and result.ok(), str(result.to_dict())))
    checks.append(report("static payload normalizes one event", len(result.events) == 1 and result.events[0].event_type == "trade" and result.events[0].source_ids, str(result.to_dict())))
    checks.append(report("event registry receives acquired event", engine.event_registry.event_count() == 1, str(engine.summary())))
    checks.append(report("acquisition summary reports background disabled", engine.summary().get("background_polling_enabled") is False, str(engine.summary())))

    print("Event Acquisition Engine Validation")
    print("=" * 64)
    failed = 0
    for name, ok, detail in checks:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}: {detail}")
        if not ok:
            failed += 1
    print(f"\nOverall status: {'PASS' if failed == 0 else 'FAIL'}")
    if failed:
        print(f"Failed: {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
