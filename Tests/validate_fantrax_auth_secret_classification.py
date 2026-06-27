"""Validate Sprint 3F.3a Fantrax auth-secret classification.

This test protects the local alpha from treating a Fantrax private league secret
or other opaque token as an authenticated browser Cookie header.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Athena.workspace import (  # noqa: E402
    SECRETS_FILE,
    classify_fantrax_auth_secret,
    load_secrets,
    save_fantrax_cookie,
    secrets_status,
)

RESULTS = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))


def main() -> int:
    original_exists = SECRETS_FILE.exists()
    original_text = SECRETS_FILE.read_text(encoding="utf-8") if original_exists else None
    try:
        opaque = classify_fantrax_auth_secret("jttzojgxme37biw2")
        record(
            "opaque_value_is_not_cookie",
            opaque.get("present") and not opaque.get("parseable_cookie") and opaque.get("format") == "opaque_value",
            str(opaque),
        )

        cookie = classify_fantrax_auth_secret("JSESSIONID=abc123; fantraxToken=xyz789")
        record(
            "browser_cookie_header_detected",
            cookie.get("parseable_cookie") and cookie.get("cookie_count") == 2,
            str(cookie),
        )

        # Start from a known valid saved cookie.
        save_fantrax_cookie("JSESSIONID=good; fantraxToken=valid")
        before = load_secrets().get("fantrax", {}).get("cookie")
        rejected = save_fantrax_cookie("opaque-league-secret")
        after = load_secrets().get("fantrax", {}).get("cookie")
        record(
            "opaque_value_does_not_overwrite_saved_cookie",
            before == after and not rejected.get("supplied_secret_saved"),
            f"before_equals_after={before == after}; status={rejected}",
        )

        status = secrets_status()
        record(
            "saved_cookie_status_is_parseable",
            status.get("fantrax_cookie_present") and status.get("fantrax_cookie_parseable") and status.get("fantrax_cookie_count") == 2,
            str(status),
        )

        # Validate Scout-facing version constant without importing/starting server.
        app_text = (PROJECT_ROOT / "Scout" / "app.py").read_text(encoding="utf-8")
        record(
            "scout_ui_labels_browser_cookie_auth",
            "v0.5.0-drop3f3a" in app_text and "Fantrax browser Cookie header" in app_text,
            "version/label check",
        )

    finally:
        if original_exists and original_text is not None:
            SECRETS_FILE.write_text(original_text, encoding="utf-8")
        elif SECRETS_FILE.exists():
            SECRETS_FILE.unlink()

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = len(RESULTS) - passed
    print("Fantrax Auth Secret Classification Validation Report")
    print("=====================================================")
    print(f"Overall status: {'PASS' if failed == 0 else 'FAIL'}")
    print(f"Passed: {passed}")
    print("Warnings: 0")
    print(f"Failed: {failed}\n")
    for name, ok, detail in RESULTS:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
