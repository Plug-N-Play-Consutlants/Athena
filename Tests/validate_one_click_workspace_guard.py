"""Validate Sprint 4A.7b one-click Fantrax live workspace guard."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def result(name: str, ok: bool, detail: str = "") -> dict:
    return {"name": name, "status": "PASS" if ok else "FAIL", "detail": detail}


def main() -> None:
    results = []
    import Providers.Fantrax.auth.connection_wizard as wizard
    importlib.reload(wizard)

    results.append(result(
        "abc123_is_placeholder",
        wizard.is_placeholder_league_id("abc123") and wizard.is_placeholder_league_id("validation_league_id"),
        "abc123 and validation IDs are blocked",
    ))

    with patch.object(wizard, "load_workspace", return_value={"workspace": {"league_id": "jttzojgxme37biw2"}}):
        selected = wizard.active_league_id("abc123")
    results.append(result(
        "workspace_id_wins_over_placeholder_fallback",
        selected == "jttzojgxme37biw2",
        selected,
    ))

    with patch.object(wizard, "load_workspace", return_value={"workspace": {"league_id": "abc123"}}):
        selected_bad = wizard.active_league_id("")
    results.append(result(
        "placeholder_workspace_not_returned",
        selected_bad == "",
        selected_bad or "blank",
    ))

    with patch.object(wizard, "load_workspace", return_value={"workspace": {"league_id": "jttzojgxme37biw2"}}), \
         patch("webbrowser.open", return_value=True):
        opened = wizard.open_fantrax_login("abc123")
    results.append(result(
        "open_login_never_uses_abc123_when_workspace_valid",
        "jttzojgxme37biw2" in opened.get("url", "") and "abc123" not in opened.get("url", ""),
        opened.get("url", ""),
    ))

    with patch.object(wizard, "load_workspace", return_value={"workspace": {"league_id": "abc123"}}), \
         patch("webbrowser.open", return_value=True):
        blocked = wizard.guided_connect_and_sync(league_id="abc123", open_browser=False)
    results.append(result(
        "one_click_blocks_placeholder_only_state",
        blocked.get("status") == "league_id_required" and blocked.get("ok") is False,
        blocked.get("message", ""),
    ))

    with patch.object(wizard, "load_workspace", return_value={"workspace": {"league_id": "abc123"}}), \
         patch.object(wizard, "update_workspace", return_value={"workspace": {"league_id": ""}}):
        clean = wizard.sanitize_live_workspace_league_id()
    results.append(result(
        "cleanup_removes_placeholder_workspace_id",
        clean.get("changed") is True and clean.get("removed_league_id") == "abc123",
        clean.get("message", ""),
    ))

    from Core.version import ATHENA_VERSION, SCOUT_VERSION
    results.append(result(
        "version_updated",
        ATHENA_VERSION == "0.5.0-drop4d1" and SCOUT_VERSION == "v0.5.0-drop4d1",
        f"Athena={ATHENA_VERSION}; Scout={SCOUT_VERSION}",
    ))

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = [r for r in results if r["status"] == "FAIL"]
    print("Fantrax One-Click Workspace Guard Validation Report")
    print("====================================================")
    print(f"Overall status: {'PASS' if not failed else 'FAIL'}")
    print(f"Passed: {passed}")
    print("Warnings: 0")
    print(f"Failed: {len(failed)}")
    print()
    for r in results:
        print(f"[{r['status']}] {r['name']}: {r['detail']}")
    raise SystemExit(0 if not failed else 1)


if __name__ == "__main__":
    main()
