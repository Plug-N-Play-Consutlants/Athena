"""Validation for Athena 0.5.2.5.0 Event Summarization Engine."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def report(name: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))
    return ok


def sample_events():
    from Knowledge.Events import normalize_event_payload
    return [
        normalize_event_payload({
            "event_id": "summary_evt_trade_001",
            "event_type": "trade",
            "sport": "nhl",
            "league": "nhl",
            "subject": "Toronto Maple Leafs",
            "summary": "Toronto acquired a right-shot defenseman.",
            "published_at": "2026-06-23T13:00:00+00:00",
            "source_id": "nhl_api",
            "source_confidence": 0.94,
            "entities": ["Toronto Maple Leafs"],
        }),
        normalize_event_payload({
            "event_id": "summary_evt_injury_001",
            "event_type": "injury",
            "sport": "nhl",
            "league": "nhl",
            "subject": "Toronto Maple Leafs",
            "summary": "A top-six forward was listed day-to-day.",
            "published_at": "2026-06-23T16:00:00+00:00",
            "source_id": "sportsnet",
            "source_confidence": 0.82,
            "entities": ["Toronto Maple Leafs"],
        }),
    ]


def main() -> int:
    print("Event Summarization Engine Validation")
    print("=" * 64)
    checks: list[bool] = []

    from Core.version import ATHENA_VERSION, ATHENA_BUILD, RELEASE_NAME
    checks.append(report("version metadata is 0.5.2.5.0 or later", ATHENA_VERSION >= "0.5.2.5.0" and ATHENA_BUILD == ATHENA_VERSION, ATHENA_VERSION))
    checks.append(report("release name is present", bool(RELEASE_NAME), RELEASE_NAME))

    from Engine.EventSummarization import EventSummarizationEngine, summarize_events, scout_event_summary_payload
    events = sample_events()
    batch = EventSummarizationEngine().summarize_events(events, title="NHL Daily Event Summary")
    payload = scout_event_summary_payload(batch)

    checks.append(report("summary batch version", batch.version >= "0.5.2.5.0", batch.version))
    checks.append(report("executive brief contains two event items", batch.brief.item_count == 2, str(batch.brief.item_count)))
    checks.append(report("executive summary is populated", "Athena summarized" in batch.brief.executive_summary, batch.brief.executive_summary))
    checks.append(report("what changed text is populated", "Latest change:" in batch.brief.what_changed, batch.brief.what_changed))
    checks.append(report("confidence summary is populated", "confidence" in batch.brief.confidence_summary.lower(), batch.brief.confidence_summary))
    checks.append(report("timeline summary is populated", bool(batch.brief.timeline_summary), batch.brief.timeline_summary))
    checks.append(report("Scout payload uses event_summary renderer", payload.get("renderer") == "event_summary", str(payload)))
    checks.append(report("Scout payload exposes items", len(payload.get("items") or []) == 2, str(payload.get("items"))))
    checks.append(report("functional alias summarize_events works", summarize_events(events).brief.item_count == 2))

    print("-" * 64)
    passed = sum(1 for item in checks if item)
    failed = len(checks) - passed
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("Overall status:", "PASS" if failed == 0 else "FAIL")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
