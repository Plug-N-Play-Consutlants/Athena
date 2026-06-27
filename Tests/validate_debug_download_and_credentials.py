"""Validate Sprint 3F.7 debug download and credential persistence behavior."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Athena.debug_export import write_debug_export
from Athena.workspace import SECRETS_FILE, save_fantrax_cookie, secrets_status
import Scout.app as scout_app


class Report:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.rows: list[tuple[str, str, str]] = []

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        if ok:
            self.passed += 1
            status = "PASS"
        else:
            self.failed += 1
            status = "FAIL"
        self.rows.append((status, name, detail))

    def print(self) -> None:
        overall = "PASS" if self.failed == 0 else "FAIL"
        print("Debug Download & Credential Persistence Validation Report")
        print("=========================================================")
        print(f"Overall status: {overall}")
        print(f"Passed: {self.passed}")
        print(f"Warnings: {self.warnings}")
        print(f"Failed: {self.failed}\n")
        for status, name, detail in self.rows:
            print(f"[{status}] {name}: {detail}")
        if self.failed:
            raise SystemExit(1)
        raise SystemExit(0)


def contains_value(value: Any, needle: str) -> bool:
    if isinstance(value, dict):
        return any(contains_value(v, needle) for v in value.values())
    if isinstance(value, list):
        return any(contains_value(v, needle) for v in value)
    if isinstance(value, str):
        return needle in value
    return False


def main() -> None:
    report = Report()
    original = SECRETS_FILE.read_text(encoding="utf-8") if SECRETS_FILE.exists() else None
    try:
        opaque = "opaque-league-secret-validation-value"
        cookie = "JSESSIONID=abc123; fantraxToken=xyz789"

        opaque_status = save_fantrax_cookie(opaque)
        report.add(
            "opaque_league_secret_persists_separately",
            bool(opaque_status.get("fantrax_league_secret_present"))
            and bool(opaque_status.get("supplied_league_secret_saved"))
            and not bool(opaque_status.get("supplied_secret_saved")),
            str({
                "league_secret_present": opaque_status.get("fantrax_league_secret_present"),
                "supplied_league_secret_saved": opaque_status.get("supplied_league_secret_saved"),
                "supplied_cookie_saved": opaque_status.get("supplied_secret_saved"),
            }),
        )

        cookie_status = save_fantrax_cookie(cookie)
        report.add(
            "browser_cookie_persists_for_authenticated_sync",
            bool(cookie_status.get("fantrax_cookie_present"))
            and bool(cookie_status.get("fantrax_cookie_parseable"))
            and int(cookie_status.get("fantrax_cookie_count") or 0) == 2,
            str({
                "cookie_present": cookie_status.get("fantrax_cookie_present"),
                "cookie_parseable": cookie_status.get("fantrax_cookie_parseable"),
                "cookie_count": cookie_status.get("fantrax_cookie_count"),
            }),
        )

        status = secrets_status()
        report.add(
            "secret_status_reports_both_credential_types",
            bool(status.get("fantrax_league_secret_present")) and bool(status.get("fantrax_cookie_present")),
            str({
                "league_secret_present": status.get("fantrax_league_secret_present"),
                "cookie_present": status.get("fantrax_cookie_present"),
            }),
        )

        export = write_debug_export(source="Validation")
        payload = export.get("payload") if isinstance(export.get("payload"), dict) else {}
        leaked = contains_value(payload, opaque) or contains_value(payload, cookie)
        report.add(
            "debug_export_redacts_persisted_credentials",
            not leaked,
            "no raw opaque secret or cookie header values found" if not leaked else "raw credential found in export payload",
        )

        app_text = Path(scout_app.__file__).read_text(encoding="utf-8")
        report.add(
            "debug_export_api_returns_download_links_not_payload_dump",
            "text_download_url" in app_text and "json_download_url" in app_text and '"payload": result.get' not in app_text,
            "download URL fields present; payload omitted from Scout export response",
        )
        report.add(
            "debug_download_endpoint_present",
            "/api/debug/download" in app_text and "Content-Disposition" in app_text,
            "download endpoint and attachment header found",
        )
        report.add(
            "scout_version",
            getattr(scout_app, "SCOUT_VERSION", "") == "v0.5.0-drop3f7",
            f"SCOUT_VERSION={getattr(scout_app, 'SCOUT_VERSION', '')}",
        )
    finally:
        if original is None:
            if SECRETS_FILE.exists():
                SECRETS_FILE.unlink()
        else:
            SECRETS_FILE.write_text(original, encoding="utf-8")

    report.print()


if __name__ == "__main__":
    main()
