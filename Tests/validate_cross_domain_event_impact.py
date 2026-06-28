"""Validation for Athena Cross-Domain Event Impact (0.5.2.2.1+)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_VERSION, ATHENA_BUILD, RELEASE_NAME, RELEASE_EPIC, RELEASE_SPRINT, VERSION_SCHEMA
from Knowledge.Events import (
    FeedRegistry,
    StaticPayloadConnector,
    acquire_events,
    fuse_events,
    normalize_event_payload,
    seed_feed_registry,
    seed_event_registry,
)
from Engine.Events import EventReasoningEngine
from Engine.CrossDomain import CrossDomainImpactEngine, default_impact_rules


def _version_tuple(value: str) -> tuple[int, int, int, int, int]:
    parts = str(value).split(".")
    if len(parts) != 5 or not all(part.isdigit() for part in parts):
        return (0, 0, 0, 0, 0)
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def _version_at_least(value: str, minimum: str) -> bool:
    return _version_tuple(value) >= _version_tuple(minimum)


def report(name: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))
    return ok


def main() -> int:
    print("Cross-Domain Event Impact Validation")
    print("=" * 64)
    checks: list[bool] = []

    checks.append(report("version is 0.5.2.2.1 or later", _version_at_least(ATHENA_VERSION, "0.5.2.2.1") and ATHENA_BUILD == ATHENA_VERSION, ATHENA_VERSION))
    checks.append(report("version schema locked", bool(re.fullmatch(r"\d+\.\d+\.\d+\.\d+\.\d+", ATHENA_VERSION)) and VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", VERSION_SCHEMA))
    checks.append(report("release metadata available", bool(RELEASE_EPIC) and bool(RELEASE_NAME), RELEASE_NAME))

    registry = seed_event_registry()
    checks.append(report("source registry still seeded", registry.source_count() >= 6 and len(registry.trusted_sources()) >= 5, f"sources={registry.source_count()} trusted={len(registry.trusted_sources())}"))

    feed_registry = seed_feed_registry()
    nhl_feeds = feed_registry.discover(sport="nhl", league="nhl")
    checks.append(report("feed registry discovers NHL official feeds", len(nhl_feeds) >= 3 and nhl_feeds[0].authority == "official", f"feeds={len(nhl_feeds)} first={nhl_feeds[0].feed_id if nhl_feeds else 'none'}"))

    payloads = [
        {
            "event_type": "injury",
            "sport": "nhl",
            "subject": "Example Player",
            "summary": "Example Player is out week-to-week.",
            "entities": ["Example Player", "Example Team"],
            "source_id": "nhl_api",
            "published_at": "2026-06-23T15:00:00+00:00",
            "source_confidence": 0.95,
        },
        {
            "event_type": "injury",
            "sport": "nhl",
            "subject": "Example Player",
            "summary": "Example Player is out week-to-week.",
            "entities": ["Example Player", "Example Team"],
            "source_id": "trusted_newswire",
            "published_at": "2026-06-23T15:05:00+00:00",
            "source_confidence": 0.84,
        },
    ]

    connector = StaticPayloadConnector("nhl_api", "nhl_injury_static_test", payloads)
    result = acquire_events(connector)
    checks.append(report("static acquisition returns canonical feed result", result.ok and len(result.events) == 2, f"status={result.status}; events={len(result.events)}"))

    fused = fuse_events(result.events)
    checks.append(report("evidence fusion merges duplicate event observations", len(fused) == 1 and fused[0].resolution_status == "corroborated" and fused[0].confidence > 0.65, f"fused={len(fused)} confidence={fused[0].confidence if fused else 'n/a'}"))

    reasoning = EventReasoningEngine().assess(fused[0].canonical_event)
    checks.append(report("live event reasoning produces impact assessment", reasoning.impact_category == "availability" and reasoning.confidence > 0.6, reasoning.to_dict().get("immediate_impact", "")))

    rules = default_impact_rules()
    checks.append(report("impact rules cover target domains", {"player", "team", "fantasy", "historical"}.issubset(set(rules["injury"])), ", ".join(rules["injury"])))

    propagation = CrossDomainImpactEngine().propagate(fused[0].canonical_event)
    domains = {impact.domain for impact in propagation.impacts}
    relationships = {delta.relationship_type for delta in propagation.graph_deltas}
    checks.append(report("cross-domain propagation targets player/team/fantasy/historical", {"player", "team", "fantasy", "historical"}.issubset(domains), ", ".join(sorted(domains))))
    checks.append(report("graph deltas generated for every impact", len(propagation.graph_deltas) == len(propagation.impacts) and len(propagation.graph_deltas) >= 4, f"deltas={len(propagation.graph_deltas)} impacts={len(propagation.impacts)}"))
    checks.append(report("fantasy value relationship present", "affects_fantasy_value" in relationships, ", ".join(sorted(relationships))))
    checks.append(report("propagation confidence remains bounded", 0.35 <= propagation.confidence <= 0.98, str(propagation.confidence)))

    print("-" * 64)
    passed = sum(1 for item in checks if item)
    failed = len(checks) - passed
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("Overall status:", "PASS" if failed == 0 else "FAIL")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
