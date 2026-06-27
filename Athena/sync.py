"""
Athena sync orchestration.

Drop 3D stabilizes sync as a thin orchestrator over the existing validated
Fetch -> Build -> Knowledge -> Intelligence scripts. Athena owns orchestration
and validation only; it does not duplicate provider/build/knowledge/intelligence
business logic.
"""

from __future__ import annotations

import contextlib
import io
import runpy
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from Core.json_utils import read_optional_json
from Core.project_paths import OUTPUT_DIR, PROJECT_ROOT, RAW_DIR
from Athena.exceptions import AthenaConfigurationError, AthenaPipelineError
from Athena.workspace import get_workspace_value, update_workspace, utc_now_iso, record_operation_result, secrets_status
from Athena.operation_result import OperationResult, recommendation_for_failure, trace_event
from Athena.capabilities import assess_capabilities, capability_dashboard

from Core.version import ATHENA_VERSION

Validator = Callable[[], tuple[bool, str, Dict[str, Any]]]


FANTRAX_FANTASY_PIPELINE: List[Dict[str, Any]] = [
    {
        "id": "fetch_fantrax_data",
        "label": "Fetch Fantrax data",
        "layer": "Fetch",
        "script": "Providers/Fantrax/fetch/fetch_all.py",
        "requires_fetch": True,
        "validator": "validate_raw_fantrax",
    },
    {
        "id": "build_player_pool_master",
        "label": "Build player pool master",
        "layer": "Build",
        "script": "Providers/Fantrax/build/player_pool_master.py",
        "validator": "validate_player_pool_master",
    },
    {
        "id": "build_player_master",
        "label": "Build player master",
        "layer": "Build",
        "script": "Providers/Fantrax/build/player_master.py",
        "validator": "validate_player_master",
    },
    {
        "id": "build_transaction_master",
        "label": "Build transaction master",
        "layer": "Build",
        "script": "Providers/Fantrax/build/transaction_master.py",
        "validator": "validate_transaction_master",
        "required": False,
        "requires_capability": "transactions",
    },
    {
        "id": "build_transaction_history",
        "label": "Build transaction history",
        "layer": "Knowledge",
        "script": "Knowledge/transaction_history.py",
        "validator": "validate_transaction_history",
        "required": False,
        "requires_capability": "transactions",
    },
    {
        "id": "build_manager_behavior",
        "label": "Build manager behavior",
        "layer": "Intelligence",
        "script": "Intelligence/manager_behavior.py",
        "validator": "validate_manager_behavior",
        "required": False,
        "requires_capability": "transactions",
    },
    {
        "id": "build_league_market",
        "label": "Build league market",
        "layer": "Intelligence",
        "script": "Intelligence/league_market.py",
        "validator": "validate_league_market",
        "required": False,
        "requires_capability": "transactions",
    },
    {
        "id": "build_knowledge_readiness",
        "label": "Build knowledge readiness",
        "layer": "Knowledge",
        "script": "Knowledge/knowledge_readiness.py",
        "validator": "validate_knowledge_readiness",
        "required": False,
    },
]


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


def _has_auth_error(payload: Any) -> bool:
    return _page_error_code(payload) in {"WARNING_NOT_LOGGED_IN", "ERROR_NOT_LOGGED_IN", "NOT_LOGGED_IN"}


def _transaction_rows(payload: Any) -> int:
    if isinstance(payload, dict):
        table = payload.get("table")
        if isinstance(table, dict) and isinstance(table.get("rows"), list):
            return len(table["rows"])
    return 0


def _count_records(payload: Any) -> int:
    if isinstance(payload, dict):
        for key in (
            "record_count",
            "manager_count",
            "transaction_count",
            "asset_movement_count",
            "raw_row_count",
        ):
            value = payload.get(key)
            if isinstance(value, int):
                return value
        for key in (
            "records",
            "transactions",
            "asset_movements",
            "team_transaction_history",
            "players",
            "teams",
        ):
            value = payload.get(key)
            if isinstance(value, list):
                return len(value)
    if isinstance(payload, list):
        return len(payload)
    return 0


def _read_json(path: Path) -> Any:
    return read_optional_json(path)


def _validate_raw_fantrax() -> tuple[bool, str, Dict[str, Any]]:
    league = _read_json(RAW_DIR / "league_info.json")
    player_pool = _read_json(RAW_DIR / "fantrax_player_pool.json")
    transactions = _read_json(RAW_DIR / "transactions.json")

    details = {
        "league_info_exists": (RAW_DIR / "league_info.json").exists(),
        "fantrax_player_pool_exists": (RAW_DIR / "fantrax_player_pool.json").exists(),
        "transactions_exists": (RAW_DIR / "transactions.json").exists(),
        "transaction_rows": _transaction_rows(transactions),
        "transactions_page_error": _page_error_code(transactions),
        "transactions_available": False,
        "transactions_unavailable_reason": "",
    }

    if not details["league_info_exists"] or not details["fantrax_player_pool_exists"]:
        return False, "Required core Fantrax files are missing: league_info.json and/or fantrax_player_pool.json.", details

    if _has_auth_error(transactions):
        details["transactions_unavailable_reason"] = "Fantrax transaction payload requires authenticated browser session."
        return True, "Core Fantrax payloads validated. Transaction payload is unavailable, so transaction-dependent intelligence will be skipped.", details

    if not details["transactions_exists"]:
        details["transactions_unavailable_reason"] = "transactions.json is missing."
        return True, "Core Fantrax payloads validated. Transaction payload is missing, so transaction-dependent intelligence will be skipped.", details

    if _transaction_rows(transactions) <= 0:
        details["transactions_unavailable_reason"] = "transactions.json contains zero transaction rows."
        return True, "Core Fantrax payloads validated. Transaction payload has zero rows, so transaction-dependent intelligence will be skipped.", details

    details["transactions_available"] = True
    return True, f"Raw Fantrax payloads validated; transaction rows: {details['transaction_rows']}.", details


def _validate_player_pool_master() -> tuple[bool, str, Dict[str, Any]]:
    payload = _read_json(OUTPUT_DIR / "player_pool_master.json")
    count = _count_records(payload)
    return count > 0, f"Player pool master records: {count}.", {"record_count": count}


def _validate_player_master() -> tuple[bool, str, Dict[str, Any]]:
    payload = _read_json(OUTPUT_DIR / "player_master.json")
    count = _count_records(payload)
    return count > 0, f"Player master records: {count}.", {"record_count": count}


def _validate_transaction_master() -> tuple[bool, str, Dict[str, Any]]:
    payload = _read_json(OUTPUT_DIR / "transaction_master.json")
    count = int(payload.get("record_count") or _count_records(payload)) if isinstance(payload, dict) else 0
    raw_rows = int(payload.get("raw_row_count") or 0) if isinstance(payload, dict) else 0
    ok = count > 0 and raw_rows > 0
    return ok, f"Canonical transactions: {count}; raw rows: {raw_rows}.", {"record_count": count, "raw_row_count": raw_rows}


def _validate_transaction_history() -> tuple[bool, str, Dict[str, Any]]:
    payload = _read_json(OUTPUT_DIR / "transaction_history.json")
    record_count = int(payload.get("record_count") or 0) if isinstance(payload, dict) else 0
    movement_count = int(payload.get("asset_movement_count") or 0) if isinstance(payload, dict) else 0
    ok = record_count > 0 and movement_count > 0
    return ok, f"Transaction history records: {record_count}; asset movements: {movement_count}.", {"record_count": record_count, "asset_movement_count": movement_count}


def _validate_manager_behavior() -> tuple[bool, str, Dict[str, Any]]:
    payload = _read_json(OUTPUT_DIR / "manager_behavior.json")
    count = int(payload.get("manager_count") or _count_records(payload)) if isinstance(payload, dict) else 0
    return count > 0, f"Managers analyzed: {count}.", {"manager_count": count}


def _validate_league_market() -> tuple[bool, str, Dict[str, Any]]:
    payload = _read_json(OUTPUT_DIR / "league_market.json")
    tx_count = int(payload.get("transaction_count") or 0) if isinstance(payload, dict) else 0
    liquidity = "unknown"
    if isinstance(payload, dict):
        market_liquidity = payload.get("market_liquidity")
        if isinstance(market_liquidity, dict):
            liquidity = str(market_liquidity.get("classification") or "unknown")
        elif market_liquidity:
            liquidity = str(market_liquidity)
    ok = tx_count > 0
    return ok, f"League market transactions: {tx_count}; liquidity: {liquidity}.", {"transaction_count": tx_count, "market_liquidity": liquidity}


def _validate_knowledge_readiness() -> tuple[bool, str, Dict[str, Any]]:
    payload = _read_json(OUTPUT_DIR / "knowledge_readiness.json")
    if not isinstance(payload, dict):
        return True, "Knowledge readiness output not available yet; non-blocking in Drop 3D.", {"readiness_score": None}
    score = payload.get("readiness_score") or payload.get("score")
    return True, f"Knowledge readiness: {score}.", {"readiness_score": score}


VALIDATORS: Dict[str, Validator] = {
    "validate_raw_fantrax": _validate_raw_fantrax,
    "validate_player_pool_master": _validate_player_pool_master,
    "validate_player_master": _validate_player_master,
    "validate_transaction_master": _validate_transaction_master,
    "validate_transaction_history": _validate_transaction_history,
    "validate_manager_behavior": _validate_manager_behavior,
    "validate_league_market": _validate_league_market,
    "validate_knowledge_readiness": _validate_knowledge_readiness,
}


def _run_script(relative_path: str) -> Dict[str, Any]:
    script_path = PROJECT_ROOT / relative_path
    if not script_path.exists():
        raise FileNotFoundError(f"Pipeline script not found: {script_path}")

    buffer = io.StringIO()
    started = time.time()
    with contextlib.redirect_stdout(buffer):
        runpy.run_path(str(script_path), run_name="__main__")
    duration = round(time.time() - started, 2)
    output = buffer.getvalue().strip()
    tail = output.splitlines()[-18:] if output else []
    return {
        "script": relative_path,
        "duration_seconds": duration,
        "log_tail": tail,
    }


def _validate_step(step: Dict[str, Any]) -> Dict[str, Any]:
    validator_name = step.get("validator")
    if not validator_name:
        return {"validation_status": "not_applicable", "validation_message": "No validator configured.", "validation_details": {}}

    validator = VALIDATORS.get(str(validator_name))
    if validator is None:
        raise AthenaPipelineError(f"Unknown sync validator: {validator_name}")

    ok, message, details = validator()
    required = bool(step.get("required", True))
    status = "pass" if ok else ("warning" if not required else "fail")
    result = {
        "validation_status": status,
        "validation_message": message,
        "validation_details": details,
    }
    if required and not ok:
        raise AthenaPipelineError(message)
    return result


def _read_output_summary() -> Dict[str, Any]:
    transaction_master = _read_json(OUTPUT_DIR / "transaction_master.json")
    transaction_history = _read_json(OUTPUT_DIR / "transaction_history.json")
    manager_behavior = _read_json(OUTPUT_DIR / "manager_behavior.json")
    league_market = _read_json(OUTPUT_DIR / "league_market.json")
    readiness = _read_json(OUTPUT_DIR / "knowledge_readiness.json")

    canonical_transactions = int(transaction_master.get("record_count") or 0) if isinstance(transaction_master, dict) else 0
    asset_movements = int(transaction_history.get("asset_movement_count") or 0) if isinstance(transaction_history, dict) else 0
    managers = int(manager_behavior.get("manager_count") or 0) if isinstance(manager_behavior, dict) else 0

    market_liquidity = "unknown"
    if isinstance(league_market, dict):
        liquidity = league_market.get("market_liquidity")
        if isinstance(liquidity, dict):
            market_liquidity = str(liquidity.get("classification") or "unknown")
        elif liquidity:
            market_liquidity = str(liquidity)

    readiness_score = None
    if isinstance(readiness, dict):
        readiness_score = readiness.get("readiness_score") or readiness.get("score")

    return {
        "canonical_transactions": canonical_transactions,
        "asset_movements": asset_movements,
        "managers_analyzed": managers,
        "market_liquidity": market_liquidity,
        "knowledge_readiness": readiness_score,
        "outputs": {
            "transaction_master": _count_records(transaction_master),
            "transaction_history": _count_records(transaction_history),
            "manager_behavior": _count_records(manager_behavior),
            "league_market": _count_records(league_market),
            "knowledge_readiness": _count_records(readiness),
        },
        "raw": {
            "league_info_exists": (RAW_DIR / "league_info.json").exists(),
            "fantrax_player_pool_exists": (RAW_DIR / "fantrax_player_pool.json").exists(),
            "transactions_exists": (RAW_DIR / "transactions.json").exists(),
            "transaction_rows": _transaction_rows(_read_json(RAW_DIR / "transactions.json")),
            "transactions_page_error": _page_error_code(_read_json(RAW_DIR / "transactions.json")),
        },
    }




def _transaction_capability_status() -> Dict[str, Any]:
    """Return whether transaction-dependent modules can run from current raw data."""
    transactions = _read_json(RAW_DIR / "transactions.json")
    page_error = _page_error_code(transactions)
    rows = _transaction_rows(transactions)
    if _has_auth_error(transactions):
        return {
            "available": False,
            "reason": "Fantrax transaction payload requires authenticated browser session.",
            "page_error": page_error,
            "transaction_rows": rows,
        }
    if not (RAW_DIR / "transactions.json").exists():
        return {
            "available": False,
            "reason": "transactions.json is missing.",
            "page_error": page_error,
            "transaction_rows": rows,
        }
    if rows <= 0:
        return {
            "available": False,
            "reason": "transactions.json contains zero transaction rows.",
            "page_error": page_error,
            "transaction_rows": rows,
        }
    return {
        "available": True,
        "reason": "transactions.json contains usable transaction rows.",
        "page_error": page_error,
        "transaction_rows": rows,
    }


def _capability_key_for_step(step: Dict[str, Any]) -> str:
    return str(step.get("requires_capability") or "")

def _pipeline_for_workspace(mode: Optional[str], provider: Optional[str]) -> List[Dict[str, Any]]:
    normalized_mode = str(mode or get_workspace_value("mode") or "fantasy_league").lower()
    normalized_provider = str(provider or get_workspace_value("provider") or "Fantrax").lower()

    if normalized_mode in {"fantasy", "fantasy_league"} and normalized_provider == "fantrax":
        return FANTRAX_FANTASY_PIPELINE

    raise AthenaConfigurationError(
        f"No sync pipeline is available for mode={normalized_mode!r}, provider={normalized_provider!r}."
    )


def sync(
    *,
    mode: Optional[str] = None,
    provider: Optional[str] = None,
    fetch: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Synchronize the active Athena workspace.

    Athena sync is intentionally a thin orchestrator. It runs the same scripts
    used by the validated transaction pipeline and validates each stage before
    continuing. Required core data failures still fail the sync, but optional
    capability gaps such as unavailable Fantrax transactions degrade gracefully
    so Athena can use the league/team/player evidence it has.
    """
    pipeline = _pipeline_for_workspace(mode, provider)
    planned_steps = [step for step in pipeline if fetch or not step.get("requires_fetch")]

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "athena_version": ATHENA_VERSION,
            "mode": mode or get_workspace_value("mode") or "fantasy_league",
            "provider": provider or get_workspace_value("provider") or "Fantrax",
            "planned_steps": planned_steps,
            "summary": _read_output_summary(),
            "capability_dashboard": capability_dashboard(assess_capabilities(provider or get_workspace_value("provider") or "Fantrax")),
        }

    started_at = utc_now_iso()
    started = time.time()
    completed_steps: List[Dict[str, Any]] = []
    developer_trace: List[Dict[str, Any]] = []
    current_step: Dict[str, Any] | None = None
    current_stage = "initialize"
    selected_provider = provider or get_workspace_value("provider") or "Fantrax"
    selected_mode = mode or get_workspace_value("mode") or "fantasy_league"

    try:
        update_workspace(last_sync_status="running", last_sync_started_at=started_at, last_sync_error="")
        developer_trace.append(trace_event("Initialize Sync", "pass", "Athena sync started.", provider=selected_provider, mode=selected_mode))
        sync_warnings: List[str] = []
        skipped_steps: List[Dict[str, Any]] = []
        capability_report: Dict[str, Any] = assess_capabilities(str(selected_provider))
        capability_status: Dict[str, Any] = dict(capability_report.get("by_key", {}))

        if str(selected_provider).strip().lower() == "fantrax":
            secret_state = secrets_status()
            parseable_cookie = bool(secret_state.get("fantrax_cookie_parseable"))
            session_message = "Fantrax browser Cookie header is available." if parseable_cookie else "Fantrax browser Cookie header is missing or malformed. Transaction-dependent modules may be unavailable."
            developer_trace.append(trace_event(
                "Validate Fantrax session",
                "pass" if parseable_cookie else "warning",
                session_message,
                secrets_file_exists=secret_state.get("secrets_file_exists"),
                fantrax_cookie_present=secret_state.get("fantrax_cookie_present"),
                fantrax_cookie_parseable=secret_state.get("fantrax_cookie_parseable"),
                fantrax_cookie_count=secret_state.get("fantrax_cookie_count"),
                fantrax_secret_format=secret_state.get("fantrax_secret_format"),
            ))
            if not parseable_cookie:
                sync_warnings.append(session_message)

        for step in planned_steps:
            capability_key = _capability_key_for_step(step)
            if capability_key and not capability_status.get(capability_key, {}).get("available", True):
                reason = str(capability_status.get(capability_key, {}).get("reason") or f"Capability {capability_key} is unavailable.")
                skipped = {
                    "id": step.get("id"),
                    "label": step.get("label"),
                    "layer": step.get("layer"),
                    "script": step.get("script"),
                    "status": "skipped",
                    "skip_reason": reason,
                    "requires_capability": capability_key,
                }
                skipped_steps.append(skipped)
                completed_steps.append(skipped)
                developer_trace.append(trace_event(str(step.get("label") or step.get("id")), "skipped", reason, requires_capability=capability_key))
                sync_warnings.append(f"Skipped {step.get('label')}: {reason}")
                continue
            current_step = step
            current_stage = str(step.get("label") or step.get("id") or "pipeline step")
            developer_trace.append(trace_event(current_stage, "running", f"Running {step.get('layer', 'Pipeline')} step.", script=step.get("script")))
            step_result = _run_script(str(step["script"]))
            completed = {
                "id": step["id"],
                "label": step["label"],
                "layer": step["layer"],
                "status": "executed",
                **step_result,
            }
            completed_steps.append(completed)
            validation = _validate_step(step)
            completed.update(validation)
            completed["status"] = "completed" if validation.get("validation_status") == "pass" else validation.get("validation_status")
            validation_status = str(validation.get("validation_status", "pass"))
            validation_details = validation.get("validation_details", {}) if isinstance(validation.get("validation_details"), dict) else {}
            developer_trace.append(trace_event(current_stage, validation_status, validation.get("validation_message", ""), validation_details=validation_details))
            if validation_status == "warning":
                sync_warnings.append(str(validation.get("validation_message") or f"{current_stage} completed with warnings."))
            if step.get("id") == "fetch_fantrax_data" or step.get("validator") == "validate_raw_fantrax":
                capability_report = assess_capabilities(str(selected_provider))
                capability_status = dict(capability_report.get("by_key", {}))
                if not capability_status.get("transactions", {}).get("available"):
                    reason = str(capability_status.get("transactions", {}).get("reason") or "Transactions unavailable.")
                    sync_warnings.append(reason)
                    developer_trace.append(trace_event("Assess transaction capability", "warning", reason, capability=capability_status.get("transactions", {})))

        capability_report = assess_capabilities(str(selected_provider))
        capability_status = dict(capability_report.get("by_key", {}))
        capability_dash = capability_dashboard(capability_report)
        summary = _read_output_summary()
        summary["capability_status"] = capability_report.get("status")
        summary["available_capabilities"] = capability_report.get("available_count", 0)
        summary["limited_capabilities"] = capability_report.get("limited_count", 0)
        finished_at = utc_now_iso()
        elapsed = round(time.time() - started, 2)
        partial = bool(sync_warnings or skipped_steps)
        operation_result = OperationResult(
            success=True,
            operation="Sync League",
            stage="completed_with_warnings" if partial else "completed",
            provider=str(selected_provider),
            confidence=0.72 if partial else 0.9,
            summary="Athena synchronized the available league data with partial capability coverage." if partial else "Athena synchronized the active league workspace.",
            reason="Required core sync stages completed. Some optional capability modules were skipped or produced warnings." if partial else "All required sync stages completed and validated.",
            recommendation="Ask Scout to analyze league/team/player data now. Reconnect Fantrax with a browser Cookie header when transaction-market intelligence is needed." if partial else "Ask Scout to analyze the league or inspect Developer Mode for refreshed output details.",
            facts=[
                f"Completed/skipped steps: {len(completed_steps)}.",
                f"Skipped optional steps: {len(skipped_steps)}.",
                f"Canonical transactions: {summary.get('canonical_transactions', 0)}.",
                f"Managers analyzed: {summary.get('managers_analyzed', 0)}.",
                f"Market liquidity: {summary.get('market_liquidity', 'unknown')}.",
                f"Capability status: {capability_report.get('status')} ({capability_report.get('available_count')} available, {capability_report.get('limited_count')} limited).",
            ],
            warnings=sync_warnings,
            developer_trace=developer_trace,
            elapsed_seconds=elapsed,
            metadata={"summary": summary, "completed_steps": completed_steps, "skipped_steps": skipped_steps, "capability_status": capability_status, "capability_dashboard": capability_dash},
        )
        update_workspace(
            last_sync_at=finished_at,
            last_sync_status="completed",
            last_sync_duration_seconds=elapsed,
            last_sync_summary=summary,
            last_sync_error="",
        )
        record_operation_result(operation_result.to_dict())
        return {
            "ok": True,
            "athena_version": ATHENA_VERSION,
            "started_at": started_at,
            "finished_at": finished_at,
            "duration_seconds": elapsed,
            "mode": selected_mode,
            "provider": selected_provider,
            "fetch_enabled": fetch,
            "completed_steps": completed_steps,
            "skipped_steps": skipped_steps,
            "warnings": sync_warnings,
            "capability_status": capability_status,
            "capability_dashboard": capability_dash,
            "partial": partial,
            "summary": summary,
            "operation_result": operation_result.to_dict(),
        }
    except Exception as exc:  # noqa: BLE001 - public orchestration boundary
        failed_at = utc_now_iso()
        error = str(exc)
        elapsed = round(time.time() - started, 2)
        summary = _read_output_summary()
        failed_step = {
            "id": current_step.get("id") if isinstance(current_step, dict) else None,
            "label": current_step.get("label") if isinstance(current_step, dict) else current_stage,
            "layer": current_step.get("layer") if isinstance(current_step, dict) else None,
            "script": current_step.get("script") if isinstance(current_step, dict) else None,
            "status": "failed",
            "error": error,
            "exception_type": type(exc).__name__,
        }
        developer_trace.append(trace_event(current_stage, "fail", error, exception_type=type(exc).__name__, failed_step=failed_step))
        operation_result = OperationResult(
            success=False,
            operation="Sync League",
            stage=current_stage,
            provider=str(selected_provider),
            confidence=0.1,
            summary="Athena could not complete league synchronization.",
            reason=error or "Unknown sync error.",
            recommendation=recommendation_for_failure(error, current_stage),
            facts=[
                f"Failed stage: {current_stage}.",
                f"Completed steps before failure: {len(completed_steps)}.",
                f"Provider: {selected_provider}.",
            ],
            errors=[error or "Unknown sync error."],
            exception_type=type(exc).__name__,
            exception_message=error,
            developer_trace=developer_trace,
            elapsed_seconds=elapsed,
            metadata={"summary": summary, "completed_steps": completed_steps, "failed_step": failed_step},
        )
        update_workspace(
            last_sync_at=failed_at,
            last_sync_status="failed",
            last_sync_error=error,
            last_sync_duration_seconds=elapsed,
            last_sync_summary=summary,
        )
        record_operation_result(operation_result.to_dict())
        return {
            "ok": False,
            "athena_version": ATHENA_VERSION,
            "started_at": started_at,
            "finished_at": failed_at,
            "duration_seconds": elapsed,
            "mode": selected_mode,
            "provider": selected_provider,
            "fetch_enabled": fetch,
            "completed_steps": completed_steps,
            "failed_step": failed_step,
            "error": error,
            "summary": summary,
            "operation_result": operation_result.to_dict(),
        }
