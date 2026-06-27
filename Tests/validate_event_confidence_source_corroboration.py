"""Validation for Athena 0.5.2.4.0 Event Confidence & Source Corroboration."""
from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_VERSION, ATHENA_BUILD, RELEASE_NAME, RELEASE_EPIC, RELEASE_SPRINT, VERSION_SCHEMA
from Knowledge.Events import normalize_event_payload
from Engine.EventConfidence import (
    EVENT_CONFIDENCE_ENGINE_VERSION,
    EventConfidenceEngine,
    confidence_label,
    profile_for_source,
    scout_confidence_payload,
    score_event_confidence,
)
from Engine.EventTimeline import build_event_timelines
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
            "event_id": "conf_evt_001a",
            "event_type": "trade",
            "sport": "nhl",
            "subject": "Example Player",
            "summary": "Example Player was traded to Example Team Two.",
            "entities": ["Example Player", "Example Team Two"],
            "source_id": "nhl_api",
            "published_at": "2026-06-23T17:30:00+00:00",
            "source_confidence": 0.96,
        },
        {
            "event_id": "conf_evt_001b",
            "event_type": "trade",
            "sport": "nhl",
            "subject": "Example Player",
            "summary": "Example Player was traded to Example Team Two.",
            "entities": ["Example Player", "Example Team Two"],
            "source_id": "trusted_newswire",
            "published_at": "2026-06-23T17:34:00+00:00",
            "source_confidence": 0.87,
        },
        {
            "event_id": "conf_evt_002",
            "event_type": "injury",
            "sport": "nhl",
            "subject": "Rumour Player",
            "summary": "Rumour Player may have left practice.",
            "entities": ["Rumour Player"],
            "source_id": "rumour_blog",
            "published_at": "2026-06-22T13:00:00+00:00",
            "source_confidence": 0.45,
        },
        {
            "event_id": "conf_evt_003",
            "event_type": "return",
            "sport": "nhl",
            "subject": "Rumour Player",
            "summary": "Rumour Player returned to practice.",
            "entities": ["Rumour Player"],
            "source_id": "nhl_api",
            "published_at": "2026-06-22T14:00:00+00:00",
            "source_confidence": 0.91,
        },
    ]
    return [normalize_event_payload(payload) for payload in payloads]


def main() -> int:
    print("Event Confidence & Source Corroboration Validation")
    print("=" * 64)
    checks: list[bool] = []

    checks.append(report("version is 0.5.2.4.0", _version_at_least(ATHENA_VERSION, "0.5.2.4.0") and ATHENA_BUILD == ATHENA_VERSION, ATHENA_VERSION))
    checks.append(report("version schema locked", bool(re.fullmatch(r"\d+\.\d+\.\d+\.\d+\.\d+", ATHENA_VERSION)) and VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", VERSION_SCHEMA))
    checks.append(report("release metadata identifies Event Confidence", RELEASE_EPIC == "5" and RELEASE_SPRINT.isdigit() and bool(RELEASE_NAME), RELEASE_NAME))
    checks.append(report("confidence engine version matches release", EVENT_CONFIDENCE_ENGINE_VERSION == "0.5.2.4.0", EVENT_CONFIDENCE_ENGINE_VERSION))

    official = profile_for_source("nhl_api")
    rumour = profile_for_source("rumour_blog")
    checks.append(report("official source scores above rumour source", official.trust_score > rumour.trust_score and official.authority == "official", f"official={official.trust_score}; rumour={rumour.trust_score}"))
    checks.append(report("confidence labels cover confirmed and weak ranges", confidence_label(91) == "confirmed" and confidence_label(45) == "weak", f"91={confidence_label(91)};45={confidence_label(45)}"))

    events = sample_events()
    result = score_event_confidence(events)
    checks.append(report("confidence result created", result.version == "0.5.2.4.0" and result.result_count >= 3, f"results={result.result_count}"))
    checks.append(report("corroboration timeline built", len(result.timeline) >= 4 and result.timeline[0].source_id, f"timeline={len(result.timeline)}"))
    checks.append(report("corroborated trade detected", any(item.subject == "Example Player" and item.corroborated and item.score >= 80 for item in result.results), str([item.to_dict() for item in result.results])))
    checks.append(report("conflicting evidence detected for same-day injury/return", result.conflict_count >= 1 and any(item.conflict_detected for item in result.results), f"conflicts={result.conflict_count}"))

    payloads = [scout_confidence_payload(item) for item in result.results]
    checks.append(report("Scout confidence payload exposes score and explanation", all("confidence_score" in item and "summary" in item for item in payloads), str(payloads)))

    timeline = build_event_timelines(events)
    propagation = CrossDomainImpactEngine().propagate(events[0])
    checks.append(report("confidence coexists with timeline intelligence", timeline.timeline_count >= 2, f"timelines={timeline.timeline_count}"))
    checks.append(report("confidence coexists with cross-domain impact", propagation.status == "propagated" and len(propagation.impacts) >= 3, f"impacts={len(propagation.impacts)}"))

    print("-" * 64)
    passed = sum(1 for item in checks if item)
    failed = len(checks) - passed
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("Overall status:", "PASS" if failed == 0 else "FAIL")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
