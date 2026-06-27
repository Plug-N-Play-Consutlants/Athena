"""Acceptance cleanup validation for v0.5.5.5.12."""
from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    results = []

    from Scout.conversation.router import route_question
    from Scout.conversation.context import load_context

    ctx = load_context()

    dallas = route_question("How good are the Dallas Stars?", ctx, mode="public")
    results.append(("dallas_routes_to_team_analysis", dallas.get("intent") == "public_analytical_route"))
    results.append(("dallas_not_public_gap", dallas.get("intent") != "public_intelligence_gap"))
    results.append(("dallas_public_aliases_collapsed", dallas.get("public_comment") == dallas.get("natural_language_response") == dallas.get("response_text") == dallas.get("scout_message")))

    matthews = route_question("Auston Matthews", ctx, mode="public")
    results.append(("player_public_aliases_collapsed", matthews.get("public_comment") == matthews.get("natural_language_response") == matthews.get("response_text") == matthews.get("scout_message")))
    results.append(("player_public_not_diagnostic", "Observed facts" not in str(matthews.get("public_comment")) and "Known limitations" not in str(matthews.get("public_comment"))))

    app = importlib.import_module("Scout.app")
    summary = app._session_answer_summary(matthews)  # type: ignore[attr-defined]
    results.append(("session_log_uses_public_comment", summary.get("text") == matthews.get("public_comment")))
    results.append(("session_log_hides_diagnostics_by_default", not summary.get("observed_facts") and not summary.get("known_limitations")))

    caps = importlib.import_module("capabilities")
    athena_caps = importlib.import_module("Athena.capabilities")
    results.append(("root_capabilities_shims_canonical", getattr(caps, "assess_capabilities") is getattr(athena_caps, "assess_capabilities")))

    dbg = importlib.import_module("debug_export")
    athena_dbg = importlib.import_module("Athena.debug_export")
    results.append(("root_debug_export_shims_canonical", getattr(dbg, "write_debug_export") is getattr(athena_dbg, "write_debug_export")))

    failed = [name for name, ok in results if not ok]
    print("Acceptance Pathway Cleanup Validation")
    print("=====================================")
    for name, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    if failed:
        raise AssertionError("Failed checks: " + ", ".join(failed))
    print("\nOverall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
