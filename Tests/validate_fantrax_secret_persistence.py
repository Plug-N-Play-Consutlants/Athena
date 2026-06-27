"""
Validate Sprint 3F.3 Fantrax secret persistence.

This validation intentionally avoids live Fantrax network calls. It verifies the
local alpha contract that Scout/Athena rely on:

1. Test & Save Connection persists a supplied auth secret through Athena.
2. The provider cookie manager reads the same persisted source used by Sync.
3. Sync preflight reports a clear diagnostic when the saved secret is missing.
4. Scout exposes the current 3F.3 UI version.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.json_utils import read_optional_json, write_json
from Core.project_paths import CONFIGURATION_DIR, REPORTS_DIR
from Athena.connect import connect_fantrax
from Athena.workspace import SECRETS_FILE, load_secrets, save_fantrax_cookie, secrets_status
from Providers.Fantrax.auth.cookie_manager import FantraxCookieManager
import Scout.app as scout_app
import Athena

REPORT_JSON = REPORTS_DIR / "fantrax_secret_persistence_validation_report.json"
REPORT_TXT = REPORTS_DIR / "fantrax_secret_persistence_validation_report.txt"


def result(name: str, status: str, detail: str) -> Dict[str, str]:
    return {"name": name, "status": status, "detail": detail}


def fake_cookie() -> str:
    return "JSESSIONID=athena-test-session; fantraxTest=stored"


def run_validation() -> Dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    backup = None
    if SECRETS_FILE.exists():
        backup = SECRETS_FILE.with_suffix(".json.3f3_validation_backup")
        shutil.copy2(SECRETS_FILE, backup)

    checks: List[Dict[str, str]] = []
    try:
        if SECRETS_FILE.exists():
            SECRETS_FILE.unlink()

        status_before = secrets_status()
        checks.append(result(
            "secret_missing_state_detected",
            "pass" if not status_before.get("fantrax_cookie_present") else "fail",
            f"initial_status={status_before}",
        ))

        connect_result = connect_fantrax(
            league_id="validation_league_id",
            auth_cookie=fake_cookie(),
            validate=False,
            mode="fantasy_league",
        )
        saved = secrets_status()
        checks.append(result(
            "connect_persists_secret",
            "pass" if connect_result.get("ok") and saved.get("fantrax_cookie_present") else "fail",
            f"ok={connect_result.get('ok')}; secret_status={saved}; result_secret_status={connect_result.get('secret_status')}",
        ))

        secrets = load_secrets()
        stored_cookie = (((secrets.get("fantrax") or {}) if isinstance(secrets, dict) else {}).get("cookie") or "")
        checks.append(result(
            "secret_value_written_to_local_file",
            "pass" if stored_cookie == fake_cookie() else "fail",
            "stored_cookie_matches_supplied_value" if stored_cookie == fake_cookie() else "stored cookie did not match supplied value",
        ))

        manager = FantraxCookieManager()
        loaded_cookie, source = manager.load_cookie_header()
        checks.append(result(
            "provider_cookie_manager_reads_saved_secret",
            "pass" if loaded_cookie == fake_cookie() and source == "secrets.local:fantrax.cookie" else "fail",
            f"source={source}; loaded={bool(loaded_cookie)}",
        ))

        parsed = manager.parse_cookie_header(loaded_cookie)
        checks.append(result(
            "saved_cookie_is_parseable",
            "pass" if parsed.get("JSESSIONID") == "athena-test-session" else "fail",
            f"parsed_cookie_count={len(parsed)}",
        ))

        # Remove the secret to verify sync preflight has a clear diagnostic and
        # does not collapse missing auth into a generic sync failure.
        if SECRETS_FILE.exists():
            SECRETS_FILE.unlink()
        sync_result = Athena.sync(mode="fantasy_league", provider="Fantrax", fetch=True)
        operation = sync_result.get("operation_result", {}) if isinstance(sync_result, dict) else {}
        reason = operation.get("reason") or sync_result.get("error") or ""
        trace = operation.get("developer_trace") or []
        checks.append(result(
            "sync_preflight_reports_missing_secret",
            "pass" if not sync_result.get("ok") and "secrets.local.json" in reason else "fail",
            f"ok={sync_result.get('ok')}; stage={operation.get('stage')}; reason={reason}",
        ))
        checks.append(result(
            "sync_trace_includes_fantrax_session_validation",
            "pass" if any(item.get("stage") == "Validate Fantrax session" for item in trace if isinstance(item, dict)) else "fail",
            f"trace={trace}",
        ))

        checks.append(result(
            "scout_ui_version",
            "pass" if scout_app.SCOUT_VERSION == "v0.5.0-drop3f3" else "fail",
            f"SCOUT_VERSION={scout_app.SCOUT_VERSION}",
        ))

    finally:
        if backup and backup.exists():
            shutil.copy2(backup, SECRETS_FILE)
            backup.unlink()
        elif SECRETS_FILE.exists():
            SECRETS_FILE.unlink()

    passed = sum(1 for item in checks if item["status"] == "pass")
    warnings = sum(1 for item in checks if item["status"] == "warn")
    failed = sum(1 for item in checks if item["status"] == "fail")
    report = {
        "overall_status": "PASS" if failed == 0 else "FAIL",
        "passed": passed,
        "warnings": warnings,
        "failed": failed,
        "checks": checks,
    }
    write_json(REPORT_JSON, report)
    lines = [
        "Fantrax Secret Persistence Validation Report",
        "============================================",
        f"Overall status: {report['overall_status']}",
        f"Passed: {passed}",
        f"Warnings: {warnings}",
        f"Failed: {failed}",
        "",
    ]
    for item in checks:
        lines.append(f"[{item['status'].upper()}] {item['name']}: {item['detail']}")
    REPORT_TXT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return report


if __name__ == "__main__":
    validation_report = run_validation()
    if validation_report["overall_status"] != "PASS":
        raise SystemExit(1)
