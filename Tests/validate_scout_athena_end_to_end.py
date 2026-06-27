"""
Validate the Scout -> Athena -> Provider full path.

Sprint 3E.4.1 is a diagnostic stabilization checkpoint. It does not add new
intelligence. It verifies the actual user path and separates:

1. public Scout behavior, which is expected to be shallow until public sports
   rule books and richer NHL data are added; and
2. fantasy-league Athena/Fantrax behavior, which must be able to connect,
   sync, build knowledge, and answer league-specific questions from evidence.

The report uses three statuses:
- pass: working as expected
- warn: usable but incomplete / skipped / needs attention
- fail: blocking issue for the fantasy-league path
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import os
import sys
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.json_utils import read_optional_json, write_json
from Core.logger import log, log_header
from Core.project_paths import CONFIGURATION_DIR, OUTPUT_DIR, RAW_DIR, REPORTS_DIR

REPORT_JSON = REPORTS_DIR / "scout_athena_end_to_end_validation_report.json"
REPORT_TXT = REPORTS_DIR / "scout_athena_end_to_end_validation_report.txt"

QUESTION_SET = [
    "Analyze my league",
    "Analyze my team",
    "Tell me about Sidney Crosby",
    "Who are the most active managers?",
    "What's the trade market like?",
]

REQUIRED_DEVELOPER_FIELDS = [
    "question",
    "context",
    "provider",
    "intent",
    "modules_executed",
    "evidence_used",
    "confidence",
    "evaluation",
    "natural_language_response",
]


def _check(name: str, status: str, message: str, details: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if status not in {"pass", "warn", "fail"}:
        status = "fail"
    return {"name": name, "status": status, "message": message, "details": details or {}}


def _safe_read_json(path: Path) -> Any:
    try:
        return read_optional_json(path)
    except Exception as exc:  # noqa: BLE001 - validation boundary
        return {"_read_error": str(exc)}


def _nested_workspace() -> Dict[str, Any]:
    payload = _safe_read_json(CONFIGURATION_DIR / "workspace.json")
    if isinstance(payload, dict) and isinstance(payload.get("workspace"), dict):
        return payload["workspace"]
    return payload if isinstance(payload, dict) else {}


def _config_provider() -> Dict[str, Any]:
    payload = _safe_read_json(CONFIGURATION_DIR / "config.json")
    provider = payload.get("provider") if isinstance(payload, dict) else None
    return provider if isinstance(provider, dict) else {}


def _secret_cookie_present() -> bool:
    payload = _safe_read_json(CONFIGURATION_DIR / "secrets.local.json")
    if not isinstance(payload, dict):
        return False
    fantrax = payload.get("fantrax")
    if isinstance(fantrax, dict) and fantrax.get("cookie"):
        return True
    if payload.get("fantrax_cookie"):
        return True
    return bool(os.environ.get("FANTRAX_COOKIE"))


def _page_error_code(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    page_error = payload.get("pageError")
    if isinstance(page_error, dict):
        return str(page_error.get("code") or "")
    responses = payload.get("responses")
    if isinstance(responses, list):
        for response in responses:
            if isinstance(response, dict):
                nested = response.get("pageError")
                if isinstance(nested, dict):
                    return str(nested.get("code") or "")
    return ""


def _transaction_rows(payload: Any) -> int:
    if isinstance(payload, dict):
        table = payload.get("table")
        if isinstance(table, dict) and isinstance(table.get("rows"), list):
            return len(table["rows"])
        records = payload.get("records")
        if isinstance(records, list):
            return len(records)
    if isinstance(payload, list):
        return len(payload)
    return 0


def _records_count(payload: Any) -> int:
    if isinstance(payload, dict):
        for key in ("record_count", "manager_count", "transaction_count", "asset_movement_count", "raw_row_count"):
            value = payload.get(key)
            if isinstance(value, int):
                return value
        for key in ("records", "teams", "players", "asset_movements"):
            value = payload.get(key)
            if isinstance(value, list):
                return len(value)
    if isinstance(payload, list):
        return len(payload)
    return 0


def _answer_has_content(answer: Dict[str, Any]) -> bool:
    return bool(answer.get("engine_conclusion") or answer.get("natural_language_response"))


def _developer_fields(answer: Dict[str, Any]) -> Tuple[List[str], Dict[str, Any]]:
    developer = answer.get("developer") if isinstance(answer, dict) else None
    developer = developer if isinstance(developer, dict) else {}
    missing = [field for field in REQUIRED_DEVELOPER_FIELDS if field not in developer]
    return missing, developer


def validate() -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    # Import and registry path.
    try:
        import Athena  # noqa: PLC0415
        from Providers.base import registered_providers, get_provider  # noqa: PLC0415
        providers = registered_providers()
        checks.append(_check(
            "athena_import_and_registry",
            "pass" if "fantrax" in providers else "fail",
            f"Registered providers: {providers}",
            {"athena_version": getattr(Athena, "__version__", "unknown"), "providers": providers},
        ))
        provider = get_provider("fantrax")
        status = provider.status().to_dict()
        checks.append(_check(
            "fantrax_provider_status",
            "pass" if status.get("provider") == "Fantrax" else "fail",
            str(status.get("message") or "Fantrax provider status loaded."),
            status,
        ))
    except Exception as exc:  # noqa: BLE001
        checks.append(_check("athena_import_and_registry", "fail", str(exc)))
        provider = None

    # Workspace and configuration sanity.
    workspace = _nested_workspace()
    config_provider = _config_provider()
    workspace_league = str(workspace.get("league_id") or "").strip()
    config_league = str(config_provider.get("league_id") or "").strip()
    provider_key = str(workspace.get("provider_key") or workspace.get("provider") or "").lower()

    workspace_status = "pass" if provider_key in {"fantrax", "fantraxprovider"} and workspace_league else "fail"
    workspace_message = f"Workspace provider={workspace.get('provider')}; league_id={workspace_league or 'missing'}."
    if workspace_league.startswith("test_"):
        workspace_status = "warn"
        workspace_message += " Workspace league_id appears to be a test value."
    checks.append(_check(
        "workspace_context",
        workspace_status,
        workspace_message,
        {
            "mode": workspace.get("mode"),
            "provider": workspace.get("provider"),
            "provider_key": workspace.get("provider_key"),
            "workspace_league_id": workspace_league,
            "workspace_name": workspace.get("name") or workspace.get("league_name"),
            "sport": workspace.get("sport"),
            "season": workspace.get("season"),
            "team_count": workspace.get("team_count"),
        },
    ))

    if config_league and workspace_league and config_league != workspace_league:
        checks.append(_check(
            "league_id_consistency",
            "warn",
            "Configuration/config.json league_id differs from Configuration/workspace.json league_id. Scout may display one context while Fantrax fetches another.",
            {"config_league_id": config_league, "workspace_league_id": workspace_league},
        ))
    else:
        checks.append(_check(
            "league_id_consistency",
            "pass" if config_league or workspace_league else "warn",
            "League id configuration is consistent." if (config_league or workspace_league) else "No league id found in config or workspace.",
            {"config_league_id": config_league, "workspace_league_id": workspace_league},
        ))

    checks.append(_check(
        "fantrax_auth_secret",
        "pass" if _secret_cookie_present() else "warn",
        "Fantrax auth cookie/secret is present." if _secret_cookie_present() else "Fantrax auth cookie/secret is missing; live connect/sync will not be reliable.",
        {"present": _secret_cookie_present()},
    ))

    # Raw and output artifact health.
    league_info = _safe_read_json(RAW_DIR / "league_info.json")
    player_pool = _safe_read_json(RAW_DIR / "fantrax_player_pool.json")
    transactions = _safe_read_json(RAW_DIR / "transactions.json")
    tx_error = _page_error_code(transactions)
    tx_rows = _transaction_rows(transactions)
    player_pool_count = _records_count(player_pool)
    league_team_count = 0
    if isinstance(league_info, dict):
        team_info = league_info.get("teamInfo")
        if isinstance(team_info, dict):
            league_team_count = len(team_info)
        elif isinstance(team_info, list):
            league_team_count = len(team_info)

    checks.append(_check(
        "raw_league_info",
        "pass" if league_team_count > 0 else "fail",
        f"League info teams detected: {league_team_count}.",
        {"exists": (RAW_DIR / "league_info.json").exists(), "team_count": league_team_count},
    ))
    checks.append(_check(
        "raw_player_pool",
        "pass" if player_pool_count > 0 else "fail",
        f"Fantrax player pool records detected: {player_pool_count}.",
        {"exists": (RAW_DIR / "fantrax_player_pool.json").exists(), "record_count": player_pool_count},
    ))
    if tx_error in {"WARNING_NOT_LOGGED_IN", "ERROR_NOT_LOGGED_IN", "NOT_LOGGED_IN"}:
        checks.append(_check(
            "raw_transactions",
            "fail",
            "Fantrax transactions payload reports not logged in. Refresh the Fantrax cookie/secret and reconnect before market/activity intelligence can work.",
            {"exists": (RAW_DIR / "transactions.json").exists(), "rows": tx_rows, "page_error": tx_error},
        ))
    else:
        checks.append(_check(
            "raw_transactions",
            "pass" if tx_rows > 0 else "warn",
            f"Fantrax transaction rows detected: {tx_rows}.",
            {"exists": (RAW_DIR / "transactions.json").exists(), "rows": tx_rows, "page_error": tx_error},
        ))

    output_expectations = [
        ("team_profiles", OUTPUT_DIR / "team_profiles.json", 1, "Athena can identify league teams and roster-value profiles."),
        ("player_master", OUTPUT_DIR / "player_master.json", 1, "Athena can identify rostered/player-pool players."),
        ("transaction_history", OUTPUT_DIR / "transaction_history.json", 1, "Athena can build transaction history."),
        ("manager_behavior", OUTPUT_DIR / "manager_behavior.json", 1, "Athena can analyze manager activity."),
        ("league_market", OUTPUT_DIR / "league_market.json", 1, "Athena can classify league market state."),
    ]
    for name, path, threshold, message in output_expectations:
        payload = _safe_read_json(path)
        count = _records_count(payload)
        status = "pass" if count >= threshold else ("warn" if name in {"transaction_history", "manager_behavior", "league_market"} else "fail")
        checks.append(_check(
            f"output_{name}",
            status,
            f"{message} Records: {count}.",
            {"path": str(path.relative_to(PROJECT_ROOT)), "record_count": count},
        ))

    # Sync dry run should be available and explain the plan without touching Fantrax.
    try:
        import Athena  # noqa: PLC0415
        dry_run = Athena.sync(mode="fantasy_league", provider="Fantrax", fetch=True, dry_run=True)
        planned_steps = dry_run.get("planned_steps") if isinstance(dry_run, dict) else []
        checks.append(_check(
            "athena_sync_dry_run",
            "pass" if dry_run.get("ok") and planned_steps else "fail",
            f"Sync dry-run planned steps: {len(planned_steps) if isinstance(planned_steps, list) else 0}.",
            {"dry_run": dry_run},
        ))
    except Exception as exc:  # noqa: BLE001
        checks.append(_check("athena_sync_dry_run", "fail", str(exc)))

    # Do not require a live sync by default because this validation must be safe
    # to run repeatedly. Allow explicit live validation from env.
    if os.environ.get("ATHENA_VALIDATE_LIVE_SYNC", "").strip().lower() in {"1", "true", "yes"}:
        try:
            import Athena  # noqa: PLC0415
            sync_result = Athena.sync(mode="fantasy_league", provider="Fantrax", fetch=True, dry_run=False)
            checks.append(_check(
                "athena_live_sync",
                "pass" if sync_result.get("ok") else "fail",
                "Live sync completed." if sync_result.get("ok") else str(sync_result.get("error") or "Live sync failed."),
                {"sync_result": sync_result},
            ))
        except Exception as exc:  # noqa: BLE001
            checks.append(_check("athena_live_sync", "fail", str(exc)))
    else:
        checks.append(_check(
            "athena_live_sync",
            "warn",
            "Live sync was skipped. Set ATHENA_VALIDATE_LIVE_SYNC=1 to exercise Fantrax fetch during validation.",
            {"skipped": True},
        ))

    # Scout public behavior: should respond, but shallow is acceptable right now.
    try:
        from Scout.conversation.context import load_context  # noqa: PLC0415
        from Scout.conversation.router import route_question  # noqa: PLC0415
        ctx = load_context()
        public_answer = route_question("Analyze the NHL", ctx, mode="public")
        public_ok = _answer_has_content(public_answer)
        checks.append(_check(
            "scout_public_interface_expected_shallow",
            "pass" if public_ok else "fail",
            "Public Scout returned a bounded response. Public rule books and rich NHL data are not expected yet.",
            {"answer": public_answer},
        ))

        for question in QUESTION_SET:
            answer = route_question(question, ctx, mode="fantasy")
            status = "pass" if _answer_has_content(answer) else "fail"
            missing_dev, developer = _developer_fields(answer)
            if missing_dev and status == "pass":
                status = "warn"
            checks.append(_check(
                f"scout_question:{question}",
                status,
                f"Intent={answer.get('intent', developer.get('intent', 'unknown'))}; developer fields missing={missing_dev}.",
                {
                    "question": question,
                    "intent": answer.get("intent") or developer.get("intent"),
                    "confidence": answer.get("confidence") or developer.get("confidence"),
                    "missing_developer_fields": missing_dev,
                    "answer_title": answer.get("title"),
                    "engine_conclusion": answer.get("engine_conclusion"),
                },
            ))
    except Exception as exc:  # noqa: BLE001
        checks.append(_check("scout_question_path", "fail", str(exc)))

    passed = sum(1 for item in checks if item["status"] == "pass")
    warned = sum(1 for item in checks if item["status"] == "warn")
    failed = sum(1 for item in checks if item["status"] == "fail")
    overall = "fail" if failed else ("warn" if warned else "pass")

    blockers = [item for item in checks if item["status"] == "fail"]
    warnings = [item for item in checks if item["status"] == "warn"]
    report = {
        "report_name": "Scout/Athena End-to-End Validation",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": overall,
        "summary": {"pass": passed, "warn": warned, "fail": failed},
        "interpretation": {
            "fantasy_league_path": "blocking" if failed else ("usable_with_warnings" if warned else "healthy"),
            "public_interface": "expected_limited_until_public_rule_books_and_richer_nhl_data_exist",
        },
        "blockers": blockers,
        "warnings": warnings,
        "checks": checks,
    }
    return report


def write_report(report: Dict[str, Any]) -> None:
    write_json(REPORT_JSON, report)
    lines = [
        "Scout/Athena End-to-End Validation Report",
        "=" * 48,
        f"Overall status: {str(report.get('overall_status', 'unknown')).upper()}",
        f"Passed: {report.get('summary', {}).get('pass', 0)}",
        f"Warnings: {report.get('summary', {}).get('warn', 0)}",
        f"Failed: {report.get('summary', {}).get('fail', 0)}",
        "",
    ]
    for item in report.get("checks", []):
        lines.append(f"[{item['status'].upper()}] {item['name']}: {item['message']}")
    if report.get("blockers"):
        lines.extend(["", "Blocking issues:"])
        for item in report["blockers"]:
            lines.append(f"- {item['name']}: {item['message']}")
    if report.get("warnings"):
        lines.extend(["", "Warnings:"])
        for item in report["warnings"]:
            lines.append(f"- {item['name']}: {item['message']}")
    REPORT_TXT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    log_header("SCOUT / ATHENA END-TO-END VALIDATION")
    report = validate()
    write_report(report)
    for line in REPORT_TXT.read_text(encoding="utf-8").splitlines():
        log(line)
    log("")
    log(f"JSON report: {REPORT_JSON}")
    log(f"Text report: {REPORT_TXT}")


if __name__ == "__main__":
    main()
