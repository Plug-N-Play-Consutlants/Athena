"""Athena/Scout debug export helpers.

The debug export is designed for Alpha testing. It captures the current
workspace, capability state, relevant Raw/Output file health, operation history,
and the latest operation payload without exposing local secrets.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable

from Core.json_utils import read_optional_json
from Core.project_paths import CONFIGURATION_DIR, LOGS_DIR, OUTPUT_DIR, RAW_DIR, REPORTS_DIR
from Core.version import SCOUT_VERSION
from Scout.conversation.composition import public_debug_summary

from Athena.capabilities import assess_capabilities, capability_dashboard
from Athena.status import get_status

DEBUG_EXPORT_VERSION = SCOUT_VERSION


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_json(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except Exception:
        return str(value)


def _count_records(payload: Any) -> int:
    if isinstance(payload, dict):
        for key in (
            "record_count",
            "team_count",
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
            "teams",
            "teamInfo",
            "players",
            "playerInfo",
            "transactions",
            "rows",
            "asset_movements",
            "team_transaction_history",
        ):
            value = payload.get(key)
            if isinstance(value, list):
                return len(value)
            if isinstance(value, dict):
                return len(value)
        table = payload.get("table")
        if isinstance(table, dict) and isinstance(table.get("rows"), list):
            return len(table["rows"])
    if isinstance(payload, list):
        return len(payload)
    return 0


def _payload_shape(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, dict):
        return {
            "type": "dict",
            "keys": sorted(str(key) for key in payload.keys())[:40],
            "record_count_guess": _count_records(payload),
        }
    if isinstance(payload, list):
        sample = payload[0] if payload else None
        sample_keys = sorted(str(key) for key in sample.keys())[:40] if isinstance(sample, dict) else []
        return {"type": "list", "record_count_guess": len(payload), "sample_keys": sample_keys}
    return {"type": type(payload).__name__, "record_count_guess": 0}


def _file_summary(path: Path) -> Dict[str, Any]:
    exists = path.exists() and path.is_file()
    error = None
    try:
        payload = read_optional_json(path) if exists else None
    except (OSError, ValueError, TypeError) as exc:
        # A corrupt diagnostic file must remain visible as a diagnostic,
        # not prevent generation of the debug export itself.
        payload = None
        error = type(exc).__name__
    result = {
        "path": str(path),
        "exists": exists,
        "size_bytes": path.stat().st_size if exists else 0,
        "shape": _payload_shape(payload) if exists else {},
    }
    if error:
        result['read_error'] = error
    return result


def _scan_files(paths: Iterable[Path]) -> Dict[str, Dict[str, Any]]:
    return {path.name: _file_summary(path) for path in paths}


def _redacted_secret_status(status: Dict[str, Any]) -> Dict[str, Any]:
    # Explicit allow-list only. Never export secret values or raw cookie text.
    keys = [
        "secrets_file_exists",
        "fantrax_cookie_present",
        "fantrax_cookie_parseable",
        "fantrax_cookie_count",
        "fantrax_secret_format",
        "fantrax_secret_looks_like_league_secret",
        "fantrax_league_secret_present",
        "fantrax_league_secret_format",
        "fantrax_league_secret_saved_at",
        "fantrax_cookie_saved_at",
        "last_rejected_secret_format",
        "last_rejected_secret_reason",
    ]
    return {key: status.get(key) for key in keys if key in status}


def build_debug_export(
    *,
    source: str = "Scout",
    latest_operation: Dict[str, Any] | None = None,
    latest_answer: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Build a redacted, portable diagnostic snapshot."""
    athena_status = get_status()
    workspace = athena_status.get("workspace") if isinstance(athena_status.get("workspace"), dict) else {}
    provider = str(workspace.get("provider") or "Fantrax")
    capability_report = assess_capabilities(provider)
    dashboard = capability_dashboard(capability_report)

    raw_files = _scan_files([
        RAW_DIR / "league_info.json",
        RAW_DIR / "fantrax_player_pool.json",
        RAW_DIR / "transactions.json",
        RAW_DIR / "draft_results.json",
        RAW_DIR / "draft_picks.json",
        RAW_DIR / "league_standings.json",
    ])
    output_files = _scan_files([
        OUTPUT_DIR / "team_profiles.json",
        OUTPUT_DIR / "player_pool_master.json",
        OUTPUT_DIR / "player_master.json",
        OUTPUT_DIR / "transaction_master.json",
        OUTPUT_DIR / "transaction_history.json",
        OUTPUT_DIR / "manager_behavior.json",
        OUTPUT_DIR / "league_market.json",
        OUTPUT_DIR / "knowledge_readiness.json",
        OUTPUT_DIR / "player_identity_coverage.json",
        OUTPUT_DIR / "PeriodScoringAudit" / "sync_manifest.json",
        OUTPUT_DIR / "PeriodScoringAudit" / "request_manifest.json",
    ])

    # Include bounded, secret-free detail so a TXT export alone establishes
    # whether the OPTIONAL audit ran. A green Sync League headline cannot.
    def safe_audit_read(path):
        try:
            return read_optional_json(path)
        except (OSError, ValueError, TypeError) as exc:
            return {'status': 'unreadable', 'reason': type(exc).__name__}
    sync_audit = safe_audit_read(OUTPUT_DIR / "PeriodScoringAudit" / "sync_manifest.json")
    request_audit = safe_audit_read(OUTPUT_DIR / "PeriodScoringAudit" / "request_manifest.json")
    identity_coverage = safe_audit_read(OUTPUT_DIR / "player_identity_coverage.json")
    last_op = workspace.get("last_operation_result") or {}
    stages = ((last_op.get("metadata") or {}).get("completed_steps") or []) if isinstance(last_op, dict) else []
    audit_step = next(({"status": s.get("status"), "validation_message": s.get("validation_message"),
                        "validation_details": s.get("validation_details"), "skip_reason": s.get("skip_reason")}
                       for s in reversed(stages) if isinstance(s, dict) and s.get("id") == "audit_historical_period_scoring"),
                      {"status": "not_recorded"})
    def audit_view(value):
        if not isinstance(value, dict):
            return {"status": "manifest_missing", "periods": {}}
        return {key: value.get(key) for key in (
            "status", "audit_scope", "league_id", "season", "audited_at", "reason",
            "attempted_count", "numeric_complete_periods", "fully_identity_complete_periods", "periods")}
    scoring_diagnostics = {
        "sync_step": audit_step,
        "sync_manifest": audit_view(sync_audit),
        "request_manifest": audit_view(request_audit),
        "identity_coverage": {"status": "available", "historical_periods_with_gaps":
                               identity_coverage.get("historical_periods_with_gaps"),
                               "historical_periods": identity_coverage.get("historical_periods", {})}
                             if isinstance(identity_coverage, dict) else {"status": "unavailable"},
    }
    secrets = athena_status.get("secrets") if isinstance(athena_status.get("secrets"), dict) else {}
    export = {
        "debug_export_version": DEBUG_EXPORT_VERSION,
        "created_at": _iso_now(),
        "source": source,
        "environment": {
            "project_root": str(CONFIGURATION_DIR.parents[0]),
            "raw_dir": str(RAW_DIR),
            "output_dir": str(OUTPUT_DIR),
            "reports_dir": str(REPORTS_DIR),
            "logs_dir": str(LOGS_DIR),
        },
        "athena": {
            "athena_version": athena_status.get("athena_version"),
            "registered_providers": athena_status.get("registered_providers"),
            "active_provider": athena_status.get("active_provider"),
        },
        "workspace": workspace,
        "secret_status_redacted": _redacted_secret_status(secrets),
        "capabilities": capability_report,
        "capability_dashboard": dashboard,
        "raw_files": raw_files,
        "output_files": output_files,
        "scoring_audit_diagnostics": scoring_diagnostics,
        "operation_history": workspace.get("operation_history", []),
        "latest_operation": latest_operation or {},
        "latest_answer": latest_answer or {},
        "notes": [
            "Secret values and browser Cookie headers are intentionally omitted.",
            "This export is intended for local Alpha debugging and can be attached to issue reports.",
        ],
    }
    return _safe_json(export)


def write_debug_export(
    *,
    source: str = "Scout",
    latest_operation: Dict[str, Any] | None = None,
    latest_answer: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Write JSON and text debug export files under Reports/."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = build_debug_export(source=source, latest_operation=latest_operation, latest_answer=latest_answer)
    stamp = _now_stamp()
    json_path = REPORTS_DIR / f"scout_debug_export_{stamp}.json"
    txt_path = REPORTS_DIR / f"scout_debug_export_{stamp}.txt"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    dashboard = payload.get("capability_dashboard") if isinstance(payload.get("capability_dashboard"), dict) else {}
    lines = dashboard.get("lines") if isinstance(dashboard.get("lines"), list) else []
    history = payload.get("operation_history") if isinstance(payload.get("operation_history"), list) else []
    text_lines = [
        "Scout / Athena Debug Export",
        "================================",
        f"Created: {payload.get('created_at')}",
        f"Athena: {(payload.get('athena') or {}).get('athena_version')}",
        f"Provider: {(payload.get('workspace') or {}).get('provider')}",
        f"League ID: {(payload.get('workspace') or {}).get('league_id')}",
        "",
        "Capability Dashboard",
        "--------------------",
    ]
    text_lines.extend(str(line) for line in lines)
    latest_answer = payload.get("latest_answer") if isinstance(payload.get("latest_answer"), dict) else {}
    if latest_answer:
        answer_payload = latest_answer.get("answer") if isinstance(latest_answer.get("answer"), dict) else {}
        text_lines.extend(["", "Latest Scout Answer", "-------------------"])
        text_lines.append(f"Question: {latest_answer.get('question') or ''}")
        summary = public_debug_summary(answer_payload)
        diagnostics = summary.get("diagnostics") if isinstance(summary.get("diagnostics"), dict) else {}
        text_lines.append(f"Title: {summary.get('title') or ''}")
        text_lines.append(f"Confidence: {summary.get('confidence')}")
        text_lines.append(f"Public response: {summary.get('public_comment') or ''}")
        conclusion = diagnostics.get("engine_conclusion") or ""
        observed = diagnostics.get("observed_facts") if isinstance(diagnostics.get("observed_facts"), list) else []
        limitations = diagnostics.get("known_limitations") if isinstance(diagnostics.get("known_limitations"), list) else []
        if conclusion or observed or limitations:
            text_lines.append("Diagnostics:")
        if conclusion:
            text_lines.append(f"  Engine conclusion: {conclusion}")
        if observed:
            text_lines.append("  Observed facts:")
            text_lines.extend(f"    - {item}" for item in observed[:12])
        if limitations:
            text_lines.append("  Known limitations:")
            text_lines.extend(f"    - {item}" for item in limitations[:12])
    text_lines.extend(["", "Historical Scoring Audit", "------------------------"])
    diagnostics = payload.get("scoring_audit_diagnostics") or {}
    step = diagnostics.get("sync_step") or {}
    text_lines.append(f"Sync optional stage: {step.get('status', 'not_recorded')} — "
                      f"{step.get('validation_message') or step.get('skip_reason') or 'No detailed result recorded'}")
    for label, key in (("Sync", "sync_manifest"), ("Scout request", "request_manifest")):
        audit = diagnostics.get(key) or {}
        text_lines.append(f"{label}: {audit.get('status')} ({audit.get('attempted_count', 0)} attempted; "
                          f"{audit.get('numeric_complete_periods', 0)} fully matched periods)"
                          + (f"; reason={audit['reason']}" if audit.get('reason') else ""))
        for period, entry in sorted((audit.get('periods') or {}).items()):
            text_lines.append(f"  - Week {period}: {entry.get('status')} "
                              f"{entry.get('numeric_matched_teams', 0)}/{entry.get('team_count', 0)} teams; "
                              f"unresolved_ACTIVE={len(entry.get('unmatched_active_ids') or [])}; "
                              f"differences={len(entry.get('point_discrepancies') or [])}"
                              + (f"; reason={entry['reason']}" if entry.get('reason') else ""))
    coverage = diagnostics.get('identity_coverage') or {}
    text_lines.append(f"Identity coverage: {coverage.get('status')}; "
                      f"archived periods with gaps={coverage.get('historical_periods_with_gaps')}")
    text_lines.extend(["", "Operation History", "-----------------"])
    for item in history[:10]:
        if isinstance(item, dict):
            marker = "✓" if item.get("success") else "✗"
            text_lines.append(f"{marker} {item.get('operation')} — {item.get('stage')}: {item.get('reason') or item.get('summary')}")
    text_lines.extend(["", "Files", "-----"])
    for section_name in ("raw_files", "output_files"):
        text_lines.append(section_name)
        files = payload.get(section_name) if isinstance(payload.get(section_name), dict) else {}
        for name, summary in files.items():
            shape = summary.get("shape") if isinstance(summary, dict) else {}
            text_lines.append(f"  - {name}: exists={summary.get('exists')} records={shape.get('record_count_guess')} size={summary.get('size_bytes')}")
    txt_path.write_text("\n".join(text_lines), encoding="utf-8")

    return {
        "ok": True,
        "json_path": str(json_path),
        "text_path": str(txt_path),
        "payload": payload,
    }
