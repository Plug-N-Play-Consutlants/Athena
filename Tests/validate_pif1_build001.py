"""Validation for PIF-1 Build 001: Intent & Entity Intelligence."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Knowledge.Intelligence.Routing.request_router import analyze_public_request


CASES = [
    ("Auston Matthews", "player_profile", "player_intelligence"),
    ("Austin Matthews", "player_profile", "player_intelligence"),
    ("Matthews", "player_profile", "player_intelligence"),
    ("Tell me about Matthews", "player_analysis", "player_intelligence"),
    ("Analyze Matthews", "player_analysis", "player_intelligence"),
    ("Compare Matthews and McDavid", "player_comparison", "player_comparison"),
    ("Who is Sebastian Aho?", "player_analysis", "disambiguate_entity"),
    ("Tell me about the Leafs", "player_analysis", "team_intelligence"),
    ("Biggest trades this week", "transaction_summary", "event_intelligence_gap"),
    ("If the NHL draft were today, who goes first?", "draft_analysis", "draft_intelligence_gap"),
]


def main() -> int:
    print("PIF-1 Build 001 Validation")
    print("=" * 52)
    failures = []
    for question, expected_intent, expected_route in CASES:
        result = analyze_public_request(question)
        actual_intent = result.intent.intent.value
        actual_route = result.route
        ok = actual_intent == expected_intent and actual_route == expected_route
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {question!r}: intent={actual_intent}; route={actual_route}; confidence={result.confidence}")
        if not ok:
            failures.append((question, expected_intent, expected_route, actual_intent, actual_route))

    if failures:
        print("\nFailures:")
        for item in failures:
            print(f"- {item[0]!r}: expected {item[1]}/{item[2]}, got {item[3]}/{item[4]}")
        return 1

    print("\nOverall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
