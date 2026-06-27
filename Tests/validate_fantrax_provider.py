"""
Validate the Fantrax provider after provider/refactor changes.

Purpose:
- Give one command that answers: did the Fantrax provider still work?
- Validate configuration, authentication, canonical fetch calls, raw file writes,
  and basic payload shape.
- Write both JSON and plain-text reports.

This is a validation harness, not a product UI and not an intelligence layer.
It validates the active canonical Fantrax provider path only; retired legacy
endpoint scripts are not part of this harness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import sys
import time
import traceback
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from Core.json_utils import read_optional_json, write_json
from Core.config import get_secret_value, reload_configuration
from Core.project_paths import RAW_DIR, REPORTS_DIR, ensure_project_dirs
from Providers.Fantrax.diagnostics import run_provider_diagnostics
from Providers.Fantrax.fantrax_client import FantraxClient


REPORT_JSON = REPORTS_DIR / "fantrax_provider_validation_report.json"
REPORT_TXT = REPORTS_DIR / "fantrax_provider_validation_report.txt"


@dataclass
class ValidationCheck:
    name: str
    status: str = "not_run"  # pass | fail | warning | not_run
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": self.details,
            "duration_seconds": round(self.duration_seconds, 3),
        }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_len(value: Any) -> int | None:
    if isinstance(value, (list, tuple, dict, str)):
        return len(value)
    return None


def _payload_summary(payload: Any) -> dict[str, Any]:
    summary: dict[str, Any] = {"type": type(payload).__name__}
    length = _safe_len(payload)
    if length is not None:
        summary["length"] = length

    if isinstance(payload, dict):
        summary["top_level_keys"] = sorted(str(key) for key in payload.keys())[:30]

        if "pageError" in payload:
            summary["page_error"] = payload.get("pageError")

        if "error" in payload:
            summary["error"] = payload.get("error")

        table = payload.get("table")
        if isinstance(table, dict):
            rows = table.get("rows")
            if isinstance(rows, list):
                summary["table_rows"] = len(rows)
            caption = table.get("caption")
            if caption:
                summary["table_caption"] = caption

        paginated = payload.get("paginatedResultSet")
        if isinstance(paginated, dict):
            summary["paginated_result_set"] = paginated

        if "record_count" in payload:
            summary["record_count"] = payload.get("record_count")
        if "is_live" in payload:
            summary["is_live"] = payload.get("is_live")
        if "source_type" in payload:
            summary["source_type"] = payload.get("source_type")

    return summary


def _is_error_payload(client: FantraxClient, payload: Any) -> tuple[bool, str]:
    if client.is_error_payload(payload):
        return True, "Fantrax returned an error payload."

    if isinstance(payload, dict) and "pageError" in payload:
        page_error = payload.get("pageError")
        code = page_error.get("code") if isinstance(page_error, dict) else page_error
        return True, f"Fantrax returned pageError: {code}"

    return False, ""


def _run_check(name: str, func: Callable[[], ValidationCheck]) -> ValidationCheck:
    started = time.perf_counter()
    try:
        check = func()
    except Exception as exc:  # noqa: BLE001 - validation should capture all failures
        check = ValidationCheck(
            name=name,
            status="fail",
            message=str(exc),
            details={"traceback": traceback.format_exc()},
        )
    check.duration_seconds = time.perf_counter() - started
    return check


def _validate_config_file() -> ValidationCheck:
    config_path = PROJECT_ROOT / "Configuration" / "config.json"
    config = read_optional_json(config_path)
    if not isinstance(config, dict):
        return ValidationCheck(
            name="configuration_file",
            status="fail",
            message="Configuration/config.json is missing or is not valid JSON.",
            details={"path": str(config_path)},
        )

    provider = config.get("provider")
    if not isinstance(provider, dict):
        return ValidationCheck(
            name="configuration_file",
            status="fail",
            message="Configuration/config.json is missing provider settings.",
            details={"path": str(config_path)},
        )

    missing = []
    for key in ["name", "sport", "base_url"]:
        if not provider.get(key):
            missing.append(f"provider.{key}")

    if missing:
        return ValidationCheck(
            name="configuration_file",
            status="fail",
            message="Required configuration values are missing.",
            details={"missing": missing},
        )

    secrets_path = PROJECT_ROOT / "Configuration" / "secrets.local.json"
    secret_cookie = get_secret_value("fantrax.cookie", "")

    return ValidationCheck(
        name="configuration_file",
        status="pass",
        message="Configuration file is valid JSON and contains provider settings.",
        details={
            "provider": provider.get("name"),
            "sport": provider.get("sport"),
            "base_url": provider.get("base_url"),
            "secrets_local_exists": secrets_path.exists(),
            "has_secret_cookie": bool(isinstance(secret_cookie, str) and secret_cookie.strip()),
            "has_legacy_auth_cookie": bool(((provider.get("auth") or {}).get("cookie"))),
            "has_headers_cookie": bool((provider.get("headers") or {}).get("Cookie") or (provider.get("headers") or {}).get("cookie")),
            "configured_cookie_count": len(provider.get("cookies") or {}),
        },
    )


def _validate_client_init() -> ValidationCheck:
    client = FantraxClient()
    client.validate_config()
    return ValidationCheck(
        name="fantrax_client_init",
        status="pass",
        message="FantraxClient initialized and configuration validation passed.",
        details={
            "provider": client.provider_name,
            "sport": client.sport,
            "workspace": client.workspace_name,
            "league_id_present": bool(client.league_id),
            "has_cookie_auth": client.has_cookie_auth(),
            "cookie_status": client.cookie_status(),
        },
    )


def _validate_provider_diagnostics() -> ValidationCheck:
    diagnostics = run_provider_diagnostics()
    status = "pass" if diagnostics.get("configuration_status") == "valid" else "fail"
    return ValidationCheck(
        name="provider_diagnostics",
        status=status,
        message="Provider diagnostics completed.",
        details=diagnostics,
    )


def _validate_fetch(
    name: str,
    filename: str,
    getter: Callable[[FantraxClient], Any],
    required_shape: Callable[[Any], tuple[bool, str]] | None = None,
) -> ValidationCheck:
    client = FantraxClient()
    payload = getter(client)
    client.save_raw_json(filename, payload)

    is_error, error_message = _is_error_payload(client, payload)
    raw_path = RAW_DIR / filename
    exists = raw_path.exists()
    summary = _payload_summary(payload)
    summary["raw_file"] = str(raw_path)
    summary["raw_file_exists"] = exists

    if is_error:
        return ValidationCheck(
            name=name,
            status="fail",
            message=error_message,
            details=summary,
        )

    if not exists:
        return ValidationCheck(
            name=name,
            status="fail",
            message="Fetch completed but raw output file was not found.",
            details=summary,
        )

    if required_shape:
        ok, shape_message = required_shape(payload)
        if not ok:
            return ValidationCheck(
                name=name,
                status="warning",
                message=shape_message,
                details=summary,
            )

    return ValidationCheck(
        name=name,
        status="pass",
        message="Fetch completed and raw output file exists.",
        details=summary,
    )


def _transactions_shape(payload: Any) -> tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "Transaction payload is not a dictionary."
    table = payload.get("table")
    if not isinstance(table, dict):
        return False, "Transaction payload does not contain table metadata."
    rows = table.get("rows")
    if not isinstance(rows, list):
        return False, "Transaction table does not contain rows."
    if not rows:
        return False, "Transaction table rows are empty."
    sample = rows[0]
    if not isinstance(sample, dict):
        return False, "First transaction row is not an object."
    for key in ["txSetId", "transactionCode", "transactionType", "scorer"]:
        if key not in sample:
            return False, f"Transaction row missing expected key: {key}"
    return True, "Transaction payload has expected row shape."


def _run_player_pool_fetch() -> ValidationCheck:
    from Providers.Fantrax.fetch.fetch_player_pool import main as fetch_player_pool_main

    fetch_player_pool_main()
    path = RAW_DIR / "fantrax_player_pool.json"
    payload = read_optional_json(path)
    summary = _payload_summary(payload)
    summary["raw_file"] = str(path)
    summary["raw_file_exists"] = path.exists()

    if not path.exists():
        return ValidationCheck(
            name="fetch_player_pool",
            status="fail",
            message="Player pool fetch completed but Raw/fantrax_player_pool.json was not found.",
            details=summary,
        )

    if isinstance(payload, dict) and not payload.get("is_live"):
        return ValidationCheck(
            name="fetch_player_pool",
            status="warning",
            message="Player pool fetch succeeded, but it used a non-live fallback source.",
            details=summary,
        )

    return ValidationCheck(
        name="fetch_player_pool",
        status="pass",
        message="Player pool fetch completed and raw output file exists.",
        details=summary,
    )


def _write_text_report(report: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("Fantrax Provider Validation Report")
    lines.append("=" * 40)
    lines.append(f"Generated: {report['generated_at']}")
    lines.append(f"Overall status: {report['overall_status'].upper()}")
    lines.append("")

    lines.append("Summary")
    lines.append("-------")
    for status, count in report["summary"].items():
        lines.append(f"{status}: {count}")
    lines.append("")

    lines.append("Checks")
    lines.append("------")
    for check in report["checks"]:
        lines.append(f"[{check['status'].upper()}] {check['name']} ({check['duration_seconds']}s)")
        lines.append(f"  {check['message']}")
        details = check.get("details") or {}
        if "table_rows" in details:
            lines.append(f"  table_rows: {details['table_rows']}")
        if "record_count" in details:
            lines.append(f"  record_count: {details['record_count']}")
        if "raw_file" in details:
            lines.append(f"  raw_file: {details['raw_file']}")
        if "page_error" in details:
            lines.append(f"  page_error: {details['page_error']}")
        if "error" in details:
            lines.append(f"  error: {details['error']}")
        lines.append("")

    REPORT_TXT.write_text("\n".join(lines), encoding="utf-8")


def run_validation() -> dict[str, Any]:
    reload_configuration()
    ensure_project_dirs()

    checks: list[ValidationCheck] = []
    checks.append(_run_check("configuration_file", _validate_config_file))
    checks.append(_run_check("fantrax_client_init", _validate_client_init))
    checks.append(_run_check("provider_diagnostics", _validate_provider_diagnostics))

    checks.append(
        _run_check(
            "fetch_league",
            lambda: _validate_fetch("fetch_league", "league_info.json", lambda client: client.get_league()),
        )
    )
    checks.append(_run_check("fetch_player_pool", _run_player_pool_fetch))
    checks.append(
        _run_check(
            "fetch_transactions",
            lambda: _validate_fetch(
                "fetch_transactions",
                "transactions.json",
                lambda client: client.get_transactions(max_results_per_page=1000),
                required_shape=_transactions_shape,
            ),
        )
    )

    summary = {"pass": 0, "warning": 0, "fail": 0, "not_run": 0}
    for check in checks:
        summary[check.status] = summary.get(check.status, 0) + 1

    if summary.get("fail", 0):
        overall_status = "fail"
    elif summary.get("warning", 0):
        overall_status = "warning"
    else:
        overall_status = "pass"

    report = {
        "report_name": "Fantrax Provider Validation Report",
        "generated_at": _utc_now(),
        "overall_status": overall_status,
        "summary": summary,
        "checks": [check.to_dict() for check in checks],
        "artifacts": {
            "json_report": str(REPORT_JSON),
            "text_report": str(REPORT_TXT),
        },
    }

    write_json(REPORT_JSON, report)
    _write_text_report(report)
    return report


def main() -> None:
    report = run_validation()
    print("Fantrax Provider Validation Report")
    print("=" * 40)
    print(f"Overall status: {report['overall_status'].upper()}")
    print(f"JSON report: {REPORT_JSON}")
    print(f"Text report: {REPORT_TXT}")
    print("")
    for check in report["checks"]:
        print(f"[{check['status'].upper()}] {check['name']}: {check['message']}")


if __name__ == "__main__":
    main()
