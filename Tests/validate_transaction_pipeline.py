"""
Validate the canonical transaction pipeline.

Runs deterministic Build -> Knowledge -> Intelligence modules related to
transactions and verifies expected output shapes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import runpy
import sys
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.json_utils import read_optional_json, write_json
from Core.logger import log_header, log
from Core.project_paths import OUTPUT_DIR, RAW_DIR, REPORTS_DIR


REPORT_JSON = REPORTS_DIR / "transaction_pipeline_validation_report.json"
REPORT_TXT = REPORTS_DIR / "transaction_pipeline_validation_report.txt"

MODULES = [
    "Providers/Fantrax/build/transaction_master.py",
    "Knowledge/transaction_history.py",
    "Intelligence/manager_behavior.py",
    "Intelligence/league_market.py",
]


def _check(name: str, status: str, message: str, details: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {"name": name, "status": status, "message": message, "details": details or {}}


def _read(path: Path) -> Any:
    return read_optional_json(path)


def _count_records(payload: Any) -> int:
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        return len(payload["records"])
    if isinstance(payload, list):
        return len(payload)
    return 0


def run_validation() -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    raw_transactions = _read(RAW_DIR / "transactions.json")
    raw_rows = 0
    if isinstance(raw_transactions, dict):
        table = raw_transactions.get("table")
        if isinstance(table, dict) and isinstance(table.get("rows"), list):
            raw_rows = len(table["rows"])
    checks.append(_check(
        "raw_transactions",
        "pass" if raw_rows > 0 else "fail",
        f"Raw transaction rows: {raw_rows}",
        {"rows": raw_rows},
    ))

    for module in MODULES:
        try:
            runpy.run_path(str(PROJECT_ROOT / module), run_name="__main__")
            checks.append(_check(module, "pass", "Module completed."))
        except Exception as exc:  # noqa: BLE001
            checks.append(_check(module, "fail", str(exc)))

    transaction_master = _read(OUTPUT_DIR / "transaction_master.json")
    transaction_history = _read(OUTPUT_DIR / "transaction_history.json")
    manager_behavior = _read(OUTPUT_DIR / "manager_behavior.json")
    league_market = _read(OUTPUT_DIR / "league_market.json")

    master_count = _count_records(transaction_master)
    checks.append(_check(
        "transaction_master_shape",
        "pass" if master_count > 0 else "fail",
        f"Canonical transactions: {master_count}",
        {
            "record_count": master_count,
            "raw_row_count": transaction_master.get("raw_row_count") if isinstance(transaction_master, dict) else None,
            "transaction_type_distribution": transaction_master.get("transaction_type_distribution") if isinstance(transaction_master, dict) else None,
        },
    ))

    history_count = int(transaction_history.get("record_count") or 0) if isinstance(transaction_history, dict) else 0
    movement_count = int(transaction_history.get("asset_movement_count") or 0) if isinstance(transaction_history, dict) else 0
    checks.append(_check(
        "transaction_history_shape",
        "pass" if history_count > 0 and movement_count > 0 else "fail",
        f"Transaction history records: {history_count}; asset movements: {movement_count}",
        {"record_count": history_count, "asset_movement_count": movement_count},
    ))

    manager_count = int(manager_behavior.get("manager_count") or 0) if isinstance(manager_behavior, dict) else 0
    checks.append(_check(
        "manager_behavior_shape",
        "pass" if manager_count > 0 else "fail",
        f"Managers analyzed: {manager_count}",
        {"manager_count": manager_count},
    ))

    market_transactions = int(league_market.get("transaction_count") or 0) if isinstance(league_market, dict) else 0
    checks.append(_check(
        "league_market_shape",
        "pass" if market_transactions > 0 else "fail",
        f"League market transactions: {market_transactions}",
        {
            "transaction_count": market_transactions,
            "market_liquidity": league_market.get("market_liquidity") if isinstance(league_market, dict) else None,
        },
    ))

    failed = sum(1 for item in checks if item["status"] == "fail")
    passed = sum(1 for item in checks if item["status"] == "pass")
    report = {
        "report_name": "Transaction Pipeline Validation Report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": "pass" if failed == 0 else "fail",
        "summary": {"pass": passed, "fail": failed},
        "checks": checks,
    }
    write_json(REPORT_JSON, report)
    _write_text(report)
    return report


def _write_text(report: Dict[str, Any]) -> None:
    lines = [
        "Transaction Pipeline Validation Report",
        "=" * 40,
        f"Overall status: {report['overall_status'].upper()}",
        f"Passed: {report['summary']['pass']}",
        f"Failed: {report['summary']['fail']}",
        "",
    ]
    for check in report["checks"]:
        lines.append(f"[{check['status'].upper()}] {check['name']}: {check['message']}")
    REPORT_TXT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    log_header("TRANSACTION PIPELINE VALIDATION")
    report = run_validation()
    for check in report["checks"]:
        log(f"[{check['status'].upper()}] {check['name']}: {check['message']}")
    log("")
    log(f"JSON report: {REPORT_JSON}")
    log(f"Text report: {REPORT_TXT}")


if __name__ == "__main__":
    main()
