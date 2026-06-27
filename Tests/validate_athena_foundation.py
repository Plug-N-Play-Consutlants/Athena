"""
Validate Athena v0.5.0 Drop 1 foundation.

Run from Spyder:
runfile('F:/Development/Sports_Intelligence_Engine_2.0/Tests/validate_athena_foundation.py', wdir='F:/Development/Sports_Intelligence_Engine_2.0')
"""

from pathlib import Path
import sys
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.json_utils import write_json
from Core.logger import log, log_header
from Core.project_paths import REPORTS_DIR

REPORT_JSON = REPORTS_DIR / "athena_foundation_validation_report.json"
REPORT_TXT = REPORTS_DIR / "athena_foundation_validation_report.txt"


def check(name, ok, message, details=None):
    return {
        "name": name,
        "status": "pass" if ok else "fail",
        "message": message,
        "details": details or {},
    }


def main():
    log_header("ATHENA FOUNDATION VALIDATION")
    checks = []

    try:
        import Athena
        checks.append(check("import_athena", True, "Athena package imported."))
    except Exception as exc:
        checks.append(check("import_athena", False, str(exc)))
        Athena = None

    if Athena:
        try:
            workspace = Athena.workspace()
            checks.append(check("workspace", isinstance(workspace, dict), "Athena workspace returned a dictionary."))
        except Exception as exc:
            checks.append(check("workspace", False, str(exc)))

        try:
            status = Athena.status()
            ok = isinstance(status, dict) and "athena_version" in status and "outputs" in status
            checks.append(check("status", ok, "Athena status returned version and output metadata.", status if ok else {}))
        except Exception as exc:
            checks.append(check("status", False, str(exc)))

        try:
            original_workspace = Athena.workspace()
            result = Athena.connect(provider="Fantrax", league_id="validation-league", mode="fantasy_league")
            ok = isinstance(result, dict) and result.get("workspace", {}).get("provider") == "Fantrax"
            checks.append(check("connect_workspace_context", ok, "Athena connect stored non-secret workspace context."))
            from Athena.workspace import save_workspace
            save_workspace(original_workspace)
        except Exception as exc:
            checks.append(check("connect_workspace_context", False, str(exc)))

        try:
            Athena.sync()
            checks.append(check("sync_reserved", False, "athena.sync() should be reserved in Drop 1."))
        except Exception as exc:
            ok = exc.__class__.__name__ == "AthenaNotImplementedError"
            checks.append(check("sync_reserved", ok, "athena.sync() is reserved for a later drop."))

        try:
            Athena.ask("Who are the most active managers?")
            checks.append(check("ask_reserved", False, "athena.ask() should be reserved in Drop 1."))
        except Exception as exc:
            ok = exc.__class__.__name__ == "AthenaNotImplementedError"
            checks.append(check("ask_reserved", ok, "athena.ask() is reserved for a later drop."))

    passed = sum(1 for item in checks if item["status"] == "pass")
    failed = sum(1 for item in checks if item["status"] == "fail")
    report = {
        "report_name": "Athena Foundation Validation",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": "pass" if failed == 0 else "fail",
        "summary": {"pass": passed, "fail": failed},
        "checks": checks,
    }
    write_json(REPORT_JSON, report)

    lines = [
        "Athena Foundation Validation Report",
        "=" * 40,
        f"Overall status: {report['overall_status'].upper()}",
        f"Passed: {passed}",
        f"Failed: {failed}",
        "",
    ]
    for item in checks:
        lines.append(f"[{item['status'].upper()}] {item['name']}: {item['message']}")
    REPORT_TXT.write_text("\n".join(lines), encoding="utf-8")

    for line in lines:
        log(line)
    log("")
    log(f"JSON report: {REPORT_JSON}")
    log(f"Text report: {REPORT_TXT}")


if __name__ == "__main__":
    main()
