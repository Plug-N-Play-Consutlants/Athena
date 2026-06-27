"""Validation for Athena 0.5.2.1.1 Live Event Reasoning."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.version import ATHENA_VERSION, RELEASE_NAME
from Engine.EventReasoning import EventReasoningEngine, affected_domains_for, significance_for
from Engine.Events import build_event_engine
from Knowledge.Events.models import EventEvidence, EventRecord, EventSourceProfile
from Knowledge.Events.evidence_fusion import fuse_event_evidence

RESULTS: list[tuple[str, bool, str]] = []


def _version_tuple(value: str) -> tuple[int, int, int, int, int]:
    parts = str(value).split(".")
    if len(parts) != 5 or not all(part.isdigit() for part in parts):
        return (0, 0, 0, 0, 0)
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def _version_at_least(value: str, minimum: str) -> bool:
    return _version_tuple(value) >= _version_tuple(minimum)


def record(name: str, ok: bool, detail: str) -> None:
    RESULTS.append((name, bool(ok), detail))


def sample_events() -> list[EventRecord]:
    return [
        EventRecord(
            event_id="evt_trade_001",
            event_type="trade",
            sport="nhl",
            league="nhl",
            subject="Toronto acquires a top-six winger",
            summary="Toronto acquired a top-six winger from Carolina.",
            occurred_at="2026-06-23T12:00:00+00:00",
            entities=["toronto-maple-leafs", "carolina-hurricanes", "top-six-winger"],
            evidence=[
                EventEvidence("nhl_api", "Official transaction notice", "2026-06-23T12:01:00+00:00", confidence=0.96),
                EventEvidence("trusted_newswire", "Newswire confirms trade", "2026-06-23T12:05:00+00:00", confidence=0.86),
            ],
        ),
        EventRecord(
            event_id="evt_injury_001",
            event_type="injury",
            sport="nhl",
            league="nhl",
            subject="Auston Matthews day-to-day",
            summary="Auston Matthews is listed as day-to-day.",
            occurred_at="2026-06-23T13:00:00+00:00",
            entities=["auston-matthews", "toronto-maple-leafs"],
            evidence=[EventEvidence("team_official", "Team injury update", "2026-06-23T13:03:00+00:00", confidence=0.88)],
        ),
    ]


def main() -> int:
    record("version", _version_at_least(ATHENA_VERSION, "0.5.2.1.0"), ATHENA_VERSION)
    record("release", bool(RELEASE_NAME), RELEASE_NAME)

    record("trade_significance", significance_for("trade", 0.9) == "major", significance_for("trade", 0.9))
    domains = affected_domains_for("injury")
    record("injury_domains", {"player", "fantasy", "events"}.issubset(set(domains)), str(domains))

    events = sample_events()
    fusion = fuse_event_evidence(events)
    record("fusion_available", fusion.fused_count >= 2, f"fused_count={fusion.fused_count}")

    engine = EventReasoningEngine()
    batch = engine.reason_about_events(events, fusion)
    record("batch_count", batch.result_count == 2, f"result_count={batch.result_count}")
    record("high_impact_count", batch.high_impact_count >= 2, f"high_impact_count={batch.high_impact_count}")

    first = batch.results[0]
    record("executive_summary", "trade" in first.executive_summary.lower(), first.executive_summary)
    record("impact_sections", bool(first.impact.immediate and first.impact.short_term and first.impact.long_term), first.impact.to_dict().__repr__())
    record("confidence_bound", 0.0 <= first.confidence <= 1.0, str(first.confidence))
    record("trace", len(first.reasoning_trace) >= 3, str(first.reasoning_trace))

    facade = build_event_engine()
    facade_batch = facade.reason(events)
    record("facade_reason", facade_batch.result_count == 2, f"result_count={facade_batch.result_count}")
    record("facade_version", _version_at_least(facade.version, "0.5.2.1.0"), facade.version)

    print("Live Event Reasoning Validation")
    print("=" * 56)
    failures = 0
    for name, ok, detail in RESULTS:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
        failures += 0 if ok else 1
    print()
    print(f"Overall status: {'PASS' if failures == 0 else 'FAIL'}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
