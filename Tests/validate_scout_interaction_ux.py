"""Validate Scout conversational interaction UX patch.

This validation is intentionally static/lightweight so it can run without
launching the browser or starting a local server.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

checks = []


def record(name: str, ok: bool, detail: str = "") -> None:
    checks.append((name, ok, detail))


try:
    from Core.version import ATHENA_VERSION, SCOUT_VERSION

    record(
        "single_version_source_3g1",
        ATHENA_VERSION == "0.5.0-drop3g1" and SCOUT_VERSION == "v0.5.0-drop3g1",
        f"Athena={ATHENA_VERSION}; Scout={SCOUT_VERSION}",
    )
except Exception as exc:
    record("single_version_source_3g1", False, str(exc))

app_path = ROOT / "Scout" / "app.py"
app_text = app_path.read_text(encoding="utf-8") if app_path.exists() else ""

record("input_clears_on_submit", "questionEl.value = '';" in app_text, "question textarea is cleared immediately after submit")
record("busy_status_present", "function setBusy" in app_text and "Scout is evaluating your question" in app_text, "visible working state added")
record("pending_turn_present", "function addPendingTurn" in app_text and "removePendingTurn" in app_text, "pending chat turn added/removed")
record("answers_append_in_chat_order", "insertAdjacentHTML('beforeend'" in app_text, "answers append as chat turns instead of replacing/appearing silently")
record("latest_answer_export_binding", "latest_answer=LATEST_ANSWER" in app_text and "LATEST_ANSWER =" in app_text, "debug export receives latest Scout answer")

responses_path = ROOT / "Scout" / "conversation" / "responses.py"
responses_text = responses_path.read_text(encoding="utf-8") if responses_path.exists() else ""
record("natural_language_response_field", "natural_language_response" in responses_text and "_natural_language_response" in responses_text, "Scout response helper emits deterministic conversational copy")

debug_path = ROOT / "Athena" / "debug_export.py"
debug_text = debug_path.read_text(encoding="utf-8") if debug_path.exists() else ""
record("debug_export_latest_answer_text", "Latest Scout Answer" in debug_text and "latest_answer" in debug_text, "text debug export includes latest answer summary")

passed = sum(1 for _, ok, _ in checks if ok)
failed = sum(1 for _, ok, _ in checks if not ok)

print("Scout Interaction UX Validation Report")
print("=======================================")
print(f"Overall status: {'PASS' if failed == 0 else 'FAIL'}")
print(f"Passed: {passed}")
print(f"Warnings: 0")
print(f"Failed: {failed}")
print()
for name, ok, detail in checks:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")

raise SystemExit(0 if failed == 0 else 1)
