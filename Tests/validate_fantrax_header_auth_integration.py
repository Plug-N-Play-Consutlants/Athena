"""Validate Sprint 4A.1 Fantrax header-auth connection UX/persistence."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.project_paths import CONFIGURATION_DIR
from Core.version import ATHENA_VERSION, SCOUT_VERSION
from Athena.workspace import classify_fantrax_auth_secret, secrets_status, save_fantrax_cookie
from Athena.connect import connect_provider

WORKSPACE_FILE = CONFIGURATION_DIR / "workspace.json"
SECRETS_FILE = CONFIGURATION_DIR / "secrets.local.json"
SCOUT_APP = PROJECT_ROOT / "Scout" / "app.py"

RESULTS = []


def record(name: str, passed: bool, detail: str = "") -> None:
    RESULTS.append((name, passed, detail))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def main() -> None:
    workspace_before = read_text(WORKSPACE_FILE)
    secrets_before = read_text(SECRETS_FILE)
    try:
        opaque = "jttzojgxme37biw2"
        cookie = "JSESSIONID=abc123; fantrax-web=xyz456"

        opaque_status = classify_fantrax_auth_secret(opaque)
        record(
            "league_secret_classified_separately",
            opaque_status.get("looks_like_league_secret") is True and opaque_status.get("parseable_cookie") is False,
            str(opaque_status),
        )

        cookie_status = classify_fantrax_auth_secret(cookie)
        record(
            "browser_cookie_header_detected",
            cookie_status.get("parseable_cookie") is True and int(cookie_status.get("cookie_count") or 0) >= 2,
            str(cookie_status),
        )

        save_fantrax_cookie(cookie)
        first = secrets_status()
        save_fantrax_cookie(opaque)
        second = secrets_status()
        record(
            "league_secret_does_not_overwrite_cookie",
            first.get("fantrax_cookie_parseable") is True
            and second.get("fantrax_cookie_parseable") is True
            and second.get("fantrax_league_secret_present") is True,
            str(second),
        )

        # Clear existing browser cookie to test the league-secret-only path.
        write_text(SECRETS_FILE, '{}')
        result = connect_provider(
            provider="fantrax",
            league_id="jttzojgxme37biw2",
            league_secret=opaque,
            auth_cookie="",
            validate=True,
            mode="fantasy_league",
        )
        record(
            "league_secret_connection_saves_without_browser_cookie",
            result.get("ok") is True and result.get("settings_saved") is True and result.get("auth_available") is False,
            str({k: result.get(k) for k in ["ok", "settings_saved", "auth_available", "message", "warning"]}),
        )

        app = SCOUT_APP.read_text(encoding="utf-8")
        record(
            "scout_ui_separates_secret_and_cookie",
            "leagueSecret" in app
            and "Authenticated browser Cookie header" in app
            and "Fantrax league secret" in app
            and "How to get the browser Cookie header" in app,
            "Scout labels found",
        )

        record(
            "version_bumped",
            ATHENA_VERSION == "0.5.0-drop4a1" and SCOUT_VERSION == "v0.5.0-drop4a1",
            f"Athena={ATHENA_VERSION}; Scout={SCOUT_VERSION}",
        )
    finally:
        if workspace_before:
            write_text(WORKSPACE_FILE, workspace_before)
        elif WORKSPACE_FILE.exists():
            WORKSPACE_FILE.unlink()
        if secrets_before:
            write_text(SECRETS_FILE, secrets_before)
        elif SECRETS_FILE.exists():
            SECRETS_FILE.unlink()

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = sum(1 for _, ok, _ in RESULTS if not ok)
    print("Fantrax Header Auth Integration Validation Report")
    print("=" * 55)
    print(f"Overall status: {'PASS' if failed == 0 else 'FAIL'}")
    print(f"Passed: {passed}")
    print("Warnings: 0")
    print(f"Failed: {failed}\n")
    for name, ok, detail in RESULTS:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    raise SystemExit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
