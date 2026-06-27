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
    payload = read_optional_json(path) if exists else None
    return {
        "path": str(path),
        "exists": exists,
        "size_bytes": path.stat().st_size if exists else 0,
        "shape": _payload_shape(payload) if exists else {},
    }


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
    ])

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
        text_lines.append(f"Title: {answer_payload.get('title') or ''}")
        text_lines.append(f"Confidence: {answer_payload.get('confidence')}")
        text_lines.append(f"Conclusion: {answer_payload.get('engine_conclusion') or ''}")
        observed = answer_payload.get("observed_facts") if isinstance(answer_payload.get("observed_facts"), list) else []
        limitations = answer_payload.get("known_limitations") if isinstance(answer_payload.get("known_limitations"), list) else []
        if observed:
            text_lines.append("Observed facts:")
            text_lines.extend(f"  - {item}" for item in observed[:12])
        if limitations:
            text_lines.append("Known limitations:")
            text_lines.extend(f"  - {item}" for item in limitations[:12])
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
