from pathlib import Path
import sys
import runpy
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.json_utils import read_optional_json, write_json
from Core.logger import log_header, log
from Core.project_paths import RAW_DIR, REPORTS_DIR
from Providers.Fantrax.fantrax_client import FantraxClient


REPORT_JSON = REPORTS_DIR / "clean_baseline_validation_report.json"
REPORT_TXT = REPORTS_DIR / "clean_baseline_validation_report.txt"


def result(name, status, message, details=None):
    return {
        "name": name,
        "status": status,
        "message": message,
        "details": details or {},
    }


def has_error(payload):
    return isinstance(payload, dict) and ("error" in payload or "pageError" in payload)


def validate():
    checks = []

    try:
        client = FantraxClient()
        client.validate_config()
        checks.append(result("fantrax_client", "pass", "Fantrax client initialized."))
    except Exception as exc:
        checks.append(result("fantrax_client", "fail", str(exc)))
        return checks

    try:
        payload = client.get_league()
        client.save_raw_json("league_info.json", payload)
        checks.append(result(
            "fetch_league",
            "fail" if has_error(payload) else "pass",
            "League fetch completed.",
        ))
    except Exception as exc:
        checks.append(result("fetch_league", "fail", str(exc)))

    try:
        runpy.run_path(
            str(PROJECT_ROOT / "Providers/Fantrax/fetch/fetch_player_pool.py"),
            run_name="__main__",
        )
        payload = read_optional_json(RAW_DIR / "fantrax_player_pool.json")
        checks.append(result(
            "fetch_player_pool",
            "pass" if isinstance(payload, dict) and payload.get("record_count", 0) > 0 else "fail",
            "Player pool fetch completed.",
            {"record_count": payload.get("record_count") if isinstance(payload, dict) else None},
        ))
    except Exception as exc:
        checks.append(result("fetch_player_pool", "fail", str(exc)))

    try:
        runpy.run_path(
            str(PROJECT_ROOT / "Providers/Fantrax/fetch/fetch_transactions.py"),
            run_name="__main__",
        )
        payload = read_optional_json(RAW_DIR / "transactions.json")
        rows = payload.get("table", {}).get("rows", []) if isinstance(payload, dict) else []
        checks.append(result(
            "fetch_transactions",
            "pass" if rows else "fail",
            "Transaction fetch completed.",
            {"rows": len(rows)},
        ))
    except Exception as exc:
        checks.append(result("fetch_transactions", "fail", str(exc)))

    required_files = [
        RAW_DIR / "league_info.json",
        RAW_DIR / "fantrax_player_pool.json",
        RAW_DIR / "transactions.json",
    ]

    for path in required_files:
        checks.append(result(
            f"file_exists:{path.name}",
            "pass" if path.exists() else "fail",
            f"{path} exists." if path.exists() else f"{path} missing.",
        ))

    return checks


def main():
    log_header("SPORTS INTELLIGENCE ENGINE CLEAN BASELINE VALIDATION")

    checks = validate()
    passed = sum(1 for c in checks if c["status"] == "pass")
    failed = sum(1 for c in checks if c["status"] == "fail")

    report = {
        "report_name": "Clean Baseline Validation",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": "pass" if failed == 0 else "fail",
        "summary": {"pass": passed, "fail": failed},
        "checks": checks,
    }

    write_json(REPORT_JSON, report)

    lines = [
        "Clean Baseline Validation Report",
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
