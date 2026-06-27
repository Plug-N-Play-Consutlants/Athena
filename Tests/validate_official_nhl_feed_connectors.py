"""Validation for Athena 0.5.1.4.0 Official NHL Feed Connectors."""
from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_BUILD, ATHENA_VERSION, RELEASE_EPIC, RELEASE_HOTFIX, RELEASE_NAME, RELEASE_PATCH, RELEASE_SPRINT, VERSION_SCHEMA
from Knowledge.Events import (
    FeedAcquisitionEngine,
    FeedResult,
    NhlOfficialApiConnector,
    acquire_nhl_official_sample,
    discover_feeds,
    nhl_connector_summary,
    seed_nhl_connector_registry,
    seed_nhl_feed_registry,
)


def report(name: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))
    return ok


def main() -> int:
    print("Official NHL Feed Connectors Validation")
    print("=" * 64)
    checks: list[bool] = []

    checks.append(report("version is 0.5.1.4.0 or later", ((ATHENA_VERSION == "0.5.1.4.0") or ATHENA_VERSION.startswith("0.5.1.5.") or ATHENA_VERSION.startswith("0.5.2.") or ATHENA_VERSION.startswith("0.5.3.")) and ATHENA_BUILD == ATHENA_VERSION, ATHENA_VERSION))
    checks.append(report("version uses locked schema", VERSION_SCHEMA == "major.epic.sprint.patch.hotfix" and bool(re.fullmatch(r"\d+\.\d+\.\d+\.\d+\.\d+", ATHENA_VERSION)), VERSION_SCHEMA))
    checks.append(report("release metadata identifies Epic 5", RELEASE_EPIC == "5", RELEASE_NAME))

    feed_registry = seed_nhl_feed_registry()
    summary = feed_registry.summarize()
    checks.append(report("NHL feed registry seeds official API feeds", {"nhl_official_schedule", "nhl_official_standings", "nhl_official_club_stats"}.issubset(set(feed_registry.feeds)), str(summary)))
    checks.append(report("official feeds are active and NHL scoped", len(feed_registry.by_sport("nhl", "nhl")) >= 4 and all(feed.sport == "nhl" for feed in feed_registry.by_sport("nhl", "nhl")), str([feed.feed_id for feed in feed_registry.by_sport("nhl", "nhl")])) )
    checks.append(report("feed discovery prioritizes official NHL feeds", discover_feeds(feed_registry, sport="nhl", league="nhl")[0].authority == "official", discover_feeds(feed_registry, sport="nhl", league="nhl")[0].feed_id))

    connector_registry = seed_nhl_connector_registry()
    checks.append(report("NHL connector registered", isinstance(connector_registry.get("nhl_official_api"), NhlOfficialApiConnector), str(connector_registry.available_types())))

    payloads = {
        "nhl_official_schedule": [
            {"id": 2026020001, "gameDate": "2026-10-08", "gameState": "scheduled", "awayTeam": {"default": "Toronto Maple Leafs"}, "homeTeam": {"default": "Montreal Canadiens"}},
            {"id": 2026020002, "gameDate": "2026-10-09", "gameState": "final", "awayTeam": {"default": "Boston Bruins"}, "homeTeam": {"default": "Ottawa Senators"}},
        ],
        "nhl_official_standings": [
            {"teamName": {"default": "Toronto Maple Leafs"}, "season": "20262027"}
        ],
    }
    engine = FeedAcquisitionEngine(feed_registry, seed_nhl_connector_registry(payloads))
    result = engine.acquire("nhl_official_schedule")
    checks.append(report("NHL schedule acquisition returns FeedResult", isinstance(result, FeedResult), type(result).__name__))
    checks.append(report("NHL schedule payload normalizes to canonical events", result.status == "success" and len(result.events) == 2, result.to_dict().get("status", "")))
    checks.append(report("schedule states map to schedule/result event types", {event.event_type for event in result.events} == {"schedule_change", "game_result"}, str([event.event_type for event in result.events])))
    checks.append(report("official source confidence is high", all(event.confidence >= 0.9 for event in result.events), str([event.confidence for event in result.events])))
    checks.append(report("feed health is marked healthy", feed_registry.health_for("nhl_official_schedule").status == "healthy", feed_registry.health_for("nhl_official_schedule").to_dict().__repr__()))

    standings = engine.acquire("nhl_official_standings")
    checks.append(report("NHL standings payload normalizes", standings.status == "success" and len(standings.events) == 1 and standings.events[0].subject == "Toronto Maple Leafs", standings.to_dict().__repr__()[:240]))

    sample = acquire_nhl_official_sample()
    checks.append(report("sample official acquisition is network-safe", sample.status == "success" and sample.events and sample.raw_count == 1, sample.to_dict().__repr__()[:240]))

    connector_summary = nhl_connector_summary()
    checks.append(report("connector summary exposes official feed ids", set(connector_summary.get("official_feed_ids", [])) == {"nhl_official_schedule", "nhl_official_standings", "nhl_official_club_stats"}, str(connector_summary)))
    checks.append(report("connector remains network-safe by default", connector_summary.get("network_safe_by_default") is True, str(connector_summary)))

    checks.append(report("connector output remains facts-only", not any(hasattr(event, "conclusion") or hasattr(event, "recommendation") for event in result.events), "Reasoning owns conclusions"))

    failed = [ok for ok in checks if not ok]
    print("\nOverall status:", "PASS" if not failed else "FAIL")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
