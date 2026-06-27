"""Acceptance validation for v0.5.5.5.17 public gap language and targeted team analysis."""
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.version import ATHENA_VERSION, SCOUT_VERSION
from Scout.conversation.router import ScoutContext, route_question


def _failures() -> list[str]:
    failures: list[str] = []
    ctx = ScoutContext()

    checks = [
        (ATHENA_VERSION >= "0.5.5.5.17", f"athena_version={ATHENA_VERSION}"),
        (SCOUT_VERSION >= "v0.5.5.5.17", f"scout_version={SCOUT_VERSION}"),
    ]
    for ok, msg in checks:
        if not ok:
            failures.append(msg)

    weakness = route_question("Leafs weakness", ctx, "public")
    weakness_text = str(weakness.get("public_comment") or "")
    if weakness.get("title") != "Toronto Maple Leafs weakness analysis":
        failures.append(f"weakness_title={weakness.get('title')}")
    if ("does not have one single weakness" not in weakness_text and "main weakness" not in weakness_text):
        failures.append("weakness_not_targeted")
    forbidden = ["Route:", "Allowed domains", "knowledge pack", "Seed context", "Observed Facts"]
    for marker in forbidden:
        if marker.lower() in weakness_text.lower():
            failures.append(f"weakness_public_leaks_{marker}")

    draft = route_question("Evaluate the leafs upcoming draft this year", ctx, "public")
    draft_text = str(draft.get("public_comment") or "")
    if draft.get("title") != "Draft outlook needs verified evidence":
        failures.append(f"draft_title={draft.get('title')}")
    if "Leafs draft evaluation" not in draft_text:
        failures.append("draft_not_team_framed")
    for marker in ["Route:", "Allowed domains", "Blocked domains", "knowledge pack", "PIF"]:
        if marker.lower() in draft_text.lower():
            failures.append(f"draft_public_leaks_{marker}")
    if draft.get("cards"):
        failures.append("draft_gap_cards_should_be_empty")

    number_one = route_question("Who will be be the number 1 draft pick?", ctx, "public")
    number_text = str(number_one.get("public_comment") or "")
    if "prospect" not in number_text.lower() or "verified" not in number_text.lower():
        failures.append("number_one_gap_not_analyst_language")
    if "knowledge pack" in number_text.lower() or "route" in number_text.lower():
        failures.append("number_one_gap_public_leak")

    return failures


def main() -> int:
    failures = _failures()
    print("Public Gap Language and Targeted Analysis Validation")
    print("=" * 56)
    if failures:
        for item in failures:
            print(f"[FAIL] {item}")
        print("Overall status: FAIL")
        return 1
    print("[PASS] version metadata")
    print("[PASS] Leafs weakness produces targeted analyst response")
    print("[PASS] draft gaps use public analyst language")
    print("[PASS] public gap answers do not expose route/domain internals")
    print("Overall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
