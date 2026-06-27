"""Import smoke test for Knowledge.Events compatibility exports.

This test intentionally runs before downstream Event validators. It verifies that
package-level imports remain stable for Event Intelligence, Multi-Sport
Connectors, Cross-Domain Impact, Timeline, Confidence, and Summarization.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def report(name: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))
    return ok


def main() -> int:
    print("Knowledge.Events Import Smoke Test")
    print("=" * 64)
    checks: list[bool] = []

    try:
        import Knowledge.Events as events
        checks.append(report("import Knowledge.Events", True, str(events.__file__)))
    except Exception as exc:
        checks.append(report("import Knowledge.Events", False, str(exc)))
        return 1

    required = [
        "canonical_event_types",
        "canonical_event_payload",
        "normalize_event_payload",
        "acquire_events",
        "fuse_events",
        "event_signature",
    ]
    for name in required:
        checks.append(report(f"export Knowledge.Events.{name}", hasattr(events, name), name))

    try:
        from Knowledge.Events import canonical_event_payload, canonical_event_types, normalize_event_payload
        payload = {
            "event_type": "injury",
            "sport": "nhl",
            "league": "nhl",
            "subject": "Smoke Test Player",
            "summary": "Smoke Test Player is day-to-day.",
            "source_id": "nhl_api",
            "source_confidence": 0.95,
        }
        normalized = normalize_event_payload(payload)
        canonical = canonical_event_payload(payload)
        types = canonical_event_types()
        checks.append(report("normalize_event_payload returns EventRecord", normalized.event_type == "injury" and normalized.league == "nhl", normalized.to_dict()))
        checks.append(report("canonical_event_payload aliases normalizer", canonical.event_id == normalized.event_id and canonical.event_type == normalized.event_type, canonical.event_id))
        checks.append(report("canonical_event_types returns canonical list", "injury" in types and "trade" in types, ", ".join(types[:6])))
    except Exception as exc:
        checks.append(report("Knowledge.Events compatibility calls", False, str(exc)))

    print("-" * 64)
    passed = sum(1 for item in checks if item)
    failed = len(checks) - passed
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("Overall status:", "PASS" if failed == 0 else "FAIL")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
