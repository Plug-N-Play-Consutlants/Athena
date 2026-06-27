"""Validate Scout 4A.2 chat layout and Fantrax auth bridge UI."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.version import ATHENA_VERSION, SCOUT_VERSION
from Scout import app as scout_app

checks = []

def record(name: str, ok: bool, detail: str = "") -> None:
    checks.append((name, ok, detail))

html = scout_app.INDEX_HTML

record(
    "version_updated",
    ATHENA_VERSION == "0.5.0-drop4a2" and SCOUT_VERSION == "v0.5.0-drop4a2" and "Drop 4A.2" in html,
    f"Athena={ATHENA_VERSION}; Scout={SCOUT_VERSION}",
)

conversation_index = html.find('id="conversation"')
prompt_index = html.find('id="promptDock"')
record(
    "conversation_above_prompt_dock",
    conversation_index != -1 and prompt_index != -1 and conversation_index < prompt_index,
    f"conversation_index={conversation_index}; prompt_index={prompt_index}",
)

record(
    "prompt_is_sticky_bottom",
    ".search { position:sticky; bottom:12px" in html,
    "sticky prompt dock CSS present",
)

record(
    "answer_appends_to_conversation",
    "insertAdjacentHTML('beforeend'" in html and "newest response appears just above the prompt" in html,
    "append-end chat behavior present",
)

record(
    "fantrax_login_button_present",
    "openFantraxBtn" in html and "Open Fantrax Login" in html,
    "open login button present",
)

record(
    "manual_cookie_labeled_advanced",
    "Advanced: authenticated browser Cookie header" in html and "advanced validation bridge" in html,
    "manual cookie path labeled as advanced bridge",
)

record(
    "open_login_endpoint_present",
    'if path == "/api/fantrax/open-login"' in scout_app.__loader__.get_source("Scout.app"),
    "server endpoint present",
)

print("Scout Chat Layout & Auth Bridge Validation Report")
print("=================================================")
passed = sum(1 for _, ok, _ in checks if ok)
failed = len(checks) - passed
status = "PASS" if failed == 0 else "FAIL"
print(f"Overall status: {status}")
print(f"Passed: {passed}")
print(f"Warnings: 0")
print(f"Failed: {failed}\n")
for name, ok, detail in checks:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
if failed:
    raise SystemExit(1)
raise SystemExit(0)
