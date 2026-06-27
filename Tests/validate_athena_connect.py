from pathlib import Path
import sys
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.json_utils import read_optional_json, write_json
from Core.logger import log_header, log
from Core.project_paths import CONFIGURATION_DIR, RAW_DIR, REPORTS_DIR

import Athena
from Athena.connect import infer_fantrax_context

REPORT_JSON = REPORTS_DIR / "athena_connect_validation_report.json"
REPORT_TXT = REPORTS_DIR / "athena_connect_validation_report.txt"
WORKSPACE_FILE = CONFIGURATION_DIR / "workspace.json"
SECRETS_FILE = CONFIGURATION_DIR / "secrets.local.json"


def result(name, status, message, details=None):
    return {"name": name, "status": status, "message": message, "details": details or {}}


def restore(path, payload, existed):
    if existed:
        write_json(path, payload)
    elif path.exists():
        path.unlink()


def validate():
    checks = []
    workspace_existed = WORKSPACE_FILE.exists()
    secrets_existed = SECRETS_FILE.exists()
    workspace_backup = read_optional_json(WORKSPACE_FILE)
    secrets_backup = read_optional_json(SECRETS_FILE)

    try:
        try:
            status_payload = Athena.status()
            checks.append(result(
                "athena_status",
                "pass" if status_payload.get("athena_version") == "0.5.0-drop2" else "fail",
                f"Athena version: {status_payload.get('athena_version')}",
            ))
        except Exception as exc:
            checks.append(result("athena_status", "fail", str(exc)))

        try:
            current_workspace = Athena.workspace().get("workspace", {})
            league_id = current_workspace.get("league_id") or "test_league_id_drop2"
            payload = Athena.connect(provider="Fantrax", league_id=league_id, validate=False)
            new_workspace = Athena.workspace().get("workspace", {})
            checks.append(result(
                "connect_without_validation",
                "pass" if payload.get("ok") and new_workspace.get("provider") == "Fantrax" else "fail",
                "Athena connect saved Fantrax workspace without provider validation.",
                {"provider": new_workspace.get("provider"), "league_id_present": bool(new_workspace.get("league_id"))},
            ))
        except Exception as exc:
            checks.append(result("connect_without_validation", "fail", str(exc)))

        try:
            league_payload = read_optional_json(RAW_DIR / "league_info.json")
            inferred = infer_fantrax_context(league_payload)
            checks.append(result(
                "infer_fantrax_context",
                "pass" if inferred.get("name") and inferred.get("team_count", 0) >= 0 else "fail",
                "Fantrax context inference returned a context object.",
                inferred,
            ))
        except Exception as exc:
            checks.append(result("infer_fantrax_context", "fail", str(exc)))

        try:
            secret_status = Athena.status().get("secrets", {})
            checks.append(result(
                "secret_metadata_safe",
                "pass" if isinstance(secret_status.get("fantrax_cookie_present"), bool) else "fail",
                "Athena status exposes secret presence only, not secret values.",
                secret_status,
            ))
        except Exception as exc:
            checks.append(result("secret_metadata_safe", "fail", str(exc)))

        try:
            from Athena.exceptions import AthenaNotImplementedError
            try:
                Athena.sync()
                checks.append(result("sync_reserved", "fail", "athena.sync() unexpectedly executed."))
            except AthenaNotImplementedError:
                checks.append(result("sync_reserved", "pass", "athena.sync() remains reserved for Drop 3."))
        except Exception as exc:
            checks.append(result("sync_reserved", "fail", str(exc)))

        try:
            from Athena.exceptions import AthenaNotImplementedError
            try:
                Athena.ask("Who are the most active managers?")
                checks.append(result("ask_reserved", "fail", "athena.ask() unexpectedly executed."))
            except AthenaNotImplementedError:
                checks.append(result("ask_reserved", "pass", "athena.ask() remains reserved for Drop 4."))
        except Exception as exc:
            checks.append(result("ask_reserved", "fail", str(exc)))

    finally:
        restore(WORKSPACE_FILE, workspace_backup, workspace_existed)
        restore(SECRETS_FILE, secrets_backup, secrets_existed)

    return checks


def main():
    log_header("ATHENA CONNECT VALIDATION")
    checks = validate()
    passed = sum(1 for check in checks if check["status"] == "pass")
    failed = sum(1 for check in checks if check["status"] == "fail")
    report = {
        "report_name": "Athena Connect Validation",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": "pass" if failed == 0 else "fail",
        "summary": {"pass": passed, "fail": failed},
        "checks": checks,
    }
    write_json(REPORT_JSON, report)
    lines = [
        "Athena Connect Validation Report",
        "=" * 40,
        f"Overall status: {report['overall_status'].upper()}",
        f"Passed: {passed}",
        f"Failed: {failed}",
        "",
    ]
    for check in checks:
        lines.append(f"[{check['status'].upper()}] {check['name']}: {check['message']}")
    REPORT_TXT.write_text("\n".join(lines), encoding="utf-8")
    for line in lines:
        log(line)
    log("")
    log(f"JSON report: {REPORT_JSON}")
    log(f"Text report: {REPORT_TXT}")


if __name__ == "__main__":
    main()
