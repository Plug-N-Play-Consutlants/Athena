"""Validation for Athena 0.5.2.3.0 Event Timeline Intelligence."""
from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_VERSION, ATHENA_BUILD, RELEASE_NAME, RELEASE_EPIC, RELEASE_SPRINT, VERSION_SCHEMA
from Knowledge.Events import EventEvidence, normalize_event_payload
from Engine.EventTimeline import (
    EVENT_TIMELINE_ENGINE_VERSION,
    EventTimelineEngine,
    build_event_timelines,
    timeline_executive_summary,
    timeline_reasoning_payload,
    timeline_risk_flags,
)
from Engine.EventReasoning import EventReasoningEngine
from Engine.CrossDomain import CrossDomainImpactEngine


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


def sample_events():
    payloads = [
        {
            "event_id": "evt_001",
            "event_type": "injury",
            "sport": "nhl",
            "subject": "Example Player",
            "summary": "Example Player left practice with an upper-body injury.",
            "entities": ["Example Player", "Example Team"],
            "source_id": "nhl_api",
            "published_at": "2026-06-20T14:00:00+00:00",
            "source_confidence": 0.93,
        },
        {
            "event_id": "evt_002",
            "event_type": "return",
            "sport": "nhl",
            "subject": "Example Player",
            "summary": "Example Player returned to full practice.",
            "entities": ["Example Player", "Example Team"],
            "source_id": "trusted_newswire",
            "published_at": "2026-06-22T16:15:00+00:00",
            "source_confidence": 0.82,
        },
        {
            "event_id": "evt_003",
            "event_type": "trade",
            "sport": "nhl",
            "subject": "Example Player",
            "summary": "Example Player was traded to Example Team Two.",
            "entities": ["Example Player", "Example Team Two"],
            "source_id": "nhl_api",
            "published_at": "2026-06-23T17:30:00+00:00",
            "source_confidence": 0.95,
        },
        {
            "event_id": "evt_004",
            "event_type": "signing",
            "sport": "nhl",
            "subject": "Other Player",
            "summary": "Other Player signed a one-year contract.",
            "entities": ["Other Player"],
            "source_id": "nhl_api",
            "published_at": "2026-06-21T12:00:00+00:00",
            "source_confidence": 0.88,
        },
    ]
    return [normalize_event_payload(payload) for payload in payloads]


def main() -> int:
    print("Event Timeline Intelligence Validation")
    print("=" * 64)
    checks: list[bool] = []

    checks.append(report("version is 0.5.2.3.0 or later", _version_at_least(ATHENA_VERSION, "0.5.2.3.0") and ATHENA_BUILD == ATHENA_VERSION, ATHENA_VERSION))
    checks.append(report("version schema locked", bool(re.fullmatch(r"\d+\.\d+\.\d+\.\d+\.\d+", ATHENA_VERSION)) and VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", VERSION_SCHEMA))
    checks.append(report("release metadata identifies Epic 5 Sprint 2", RELEASE_EPIC == "5" and RELEASE_SPRINT.isdigit() and bool(RELEASE_NAME), RELEASE_NAME))
    checks.append(report("timeline engine version matches release", EVENT_TIMELINE_ENGINE_VERSION == "0.5.2.3.0", EVENT_TIMELINE_ENGINE_VERSION))

    events = sample_events()
    result = build_event_timelines(events)
    checks.append(report("timeline build result created", result.version == "0.5.2.3.0" and result.timeline_count == 2, f"timelines={result.timeline_count}"))

    timelines = {timeline.subject: timeline for timeline in result.timelines}
    primary = timelines.get("Example Player")
    checks.append(report("related events grouped by subject", primary is not None and primary.event_count == 3, f"event_count={primary.event_count if primary else 'n/a'}"))
    checks.append(report("timeline nodes sorted chronologically", primary is not None and [node.event_id for node in primary.nodes] == ["evt_001", "evt_002", "evt_003"], ",".join(node.event_id for node in primary.nodes) if primary else "n/a"))
    checks.append(report("timeline links connect sequence", primary is not None and len(primary.links) == 2 and all(link.relationship == "followed_by" for link in primary.links), f"links={len(primary.links) if primary else 'n/a'}"))
    checks.append(report("timeline narrative generated", primary is not None and "traces Example Player" in primary.narrative, primary.narrative if primary else "n/a"))
    checks.append(report("timeline confidence bounded", primary is not None and 0.50 <= primary.confidence <= 0.98, str(primary.confidence if primary else "n/a")))

    summary = timeline_executive_summary(primary) if primary else ""
    flags = timeline_risk_flags(primary) if primary else []
    payload = timeline_reasoning_payload(primary) if primary else {}
    checks.append(report("executive timeline summary recognizes material sequence", "high-significance" in summary or "related sequence" in summary, summary))
    checks.append(report("timeline risk flags include context and availability", {"availability_risk", "context_change"}.issubset(set(flags)), ",".join(flags)))
    checks.append(report("timeline reasoning payload includes range and confidence", bool(payload.get("first_seen")) and bool(payload.get("last_seen")) and payload.get("confidence", 0) > 0.5, str(payload)))

    reasoning = EventReasoningEngine().reason_about_event(events[0])
    propagation = CrossDomainImpactEngine().propagate(events[0])
    checks.append(report("timeline coexists with live event reasoning", getattr(reasoning, "confidence", 0) > 0.5, reasoning.impact.significance))
    checks.append(report("timeline coexists with cross-domain propagation", propagation.status == "propagated" and len(propagation.impacts) >= 3, f"impacts={len(propagation.impacts)}"))

    print("-" * 64)
    passed = sum(1 for item in checks if item)
    failed = len(checks) - passed
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("Overall status:", "PASS" if failed == 0 else "FAIL")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
