"""Validate Sprint 4A.7 / 4B.2a Fantrax connect-and-sync workflow."""

from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.json_utils import write_json


def result(name: str, ok: bool, detail: str = "") -> dict:
    return {"name": name, "status": "PASS" if ok else "FAIL", "detail": detail}


def main() -> None:
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        temp = Path(tmp)
        os.environ["ATHENA_SECRETS_FILE"] = str(temp / "external" / "secrets.local.json")

        import Core.credential_store as cs
        importlib.reload(cs)

        repo_secret = cs.REPO_SECRETS_FILE
        original_repo_payload = repo_secret.read_text(encoding="utf-8") if repo_secret.exists() else None
        try:
            write_json(repo_secret, {"fantrax": {"league_secret": "league-secret-from-repo", "cookie": "sessionId=abc; jwt=def"}})
            migrated = cs.load_persistent_secrets()
            status = cs.credential_status()
            results.append(result(
                "persistent_store_migrates_repo_secret",
                migrated.get("fantrax", {}).get("league_secret") == "league-secret-from-repo" and status.get("fantrax_cookie_parseable"),
                f"store={status.get('secrets_file')}; cookie_count={status.get('fantrax_cookie_count')}",
            ))

            # Simulate patch replacement / cleanup removing repo-local secrets.
            repo_secret.unlink(missing_ok=True)
            status_after = cs.credential_status()
            results.append(result(
                "credentials_survive_repo_secret_removal",
                status_after.get("fantrax_league_secret_present") and status_after.get("fantrax_cookie_parseable"),
                f"external_store={status_after.get('secrets_file')}",
            ))
        finally:
            if original_repo_payload is not None:
                repo_secret.write_text(original_repo_payload, encoding="utf-8")
            else:
                repo_secret.unlink(missing_ok=True)

        opaque = cs.classify_auth_value("jttzojgxme37biw2")
        cookie = cs.classify_auth_value("sessionId=abc; jwt=def")
        results.append(result(
            "auth_values_classified_separately",
            opaque.get("looks_like_league_secret") and not opaque.get("parseable_cookie") and cookie.get("parseable_cookie"),
            f"opaque={opaque.get('format')}; cookie_count={cookie.get('cookie_count')}",
        ))

        import Providers.Fantrax.auth.connection_wizard as wizard
        importlib.reload(wizard)
        with patch.object(wizard, "load_workspace", return_value={"workspace": {"league_id": "real123"}}), \
             patch("webbrowser.open", return_value=True):
            opened = wizard.open_fantrax_login("abc123")
        results.append(result(
            "open_fantrax_login_uses_workspace_not_placeholder",
            opened.get("ok") and "real123" in opened.get("url", "") and "abc123" not in opened.get("url", ""),
            opened.get("url", ""),
        ))

        # Missing browser session should not pretend one-click auth is complete.
        os.environ["ATHENA_SECRETS_FILE"] = str(temp / "external2" / "secrets.local.json")
        importlib.reload(cs)
        # Prevent the bounded no-cookie scenario from migrating any real repo-local
        # cookie that may exist on the developer machine.
        cs.REPO_SECRETS_FILE = temp / "nonexistent_repo_secrets.local.json"
        importlib.reload(wizard)
        with patch("Core.credential_store.REPO_SECRETS_FILE", temp / "nonexistent_repo_secrets.local.json"), \
             patch("webbrowser.open", return_value=True):
            needs_auth = wizard.guided_connect_and_sync(league_id="real123", league_secret="league-secret", open_browser=True)
        results.append(result(
            "one_click_bounded_without_captured_browser_session",
            needs_auth.get("status") == "browser_session_required" and needs_auth.get("ok") is False,
            needs_auth.get("message", ""),
        ))

        # With saved cookie, workflow should call Athena connect/sync. Mock network work.
        cs.save_fantrax_credentials(league_secret="league-secret", cookie_header="sessionId=abc; jwt=def")
        with patch("webbrowser.open", return_value=True), \
             patch("Athena.connect_fantrax", return_value={"ok": True, "message": "connected"}), \
             patch("Athena.sync", return_value={"ok": True, "summary": {"canonical_transactions": 2, "managers_analyzed": 1}}):
            done = wizard.guided_connect_and_sync(league_id="real123", open_browser=True, run_sync=True)
        results.append(result(
            "one_click_connects_and_syncs_when_cookie_ready",
            done.get("ok") and done.get("status") == "connected_and_synced" and done.get("sync_result", {}).get("summary", {}).get("canonical_transactions") == 2,
            done.get("status", ""),
        ))

        app_text = (PROJECT_ROOT / "Scout" / "app.py").read_text(encoding="utf-8")
        results.append(result(
            "scout_endpoint_and_button_present",
            "/api/fantrax/connect-and-sync" in app_text and "Connect Fantrax & Sync" in app_text,
            "endpoint/button present",
        ))

        from Core.version import ATHENA_VERSION, SCOUT_VERSION
        results.append(result(
            "version_updated",
            ATHENA_VERSION == "0.5.0-drop4d1" and SCOUT_VERSION == "v0.5.0-drop4d1",
            f"Athena={ATHENA_VERSION}; Scout={SCOUT_VERSION}",
        ))

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = [r for r in results if r["status"] == "FAIL"]
    print("Fantrax One-Click Connect Validation Report")
    print("================================================")
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
