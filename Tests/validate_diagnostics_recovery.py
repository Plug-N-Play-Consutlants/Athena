"""Validate Sprint 3F.2 Diagnostics & Recovery.

This validation uses local monkeypatches only. It verifies that sync failures no
longer collapse into an opaque "Sync failed" message and that Scout can render
operation diagnostics without requiring a live Fantrax call.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.project_paths import CONFIGURATION_DIR
from Athena.workspace import load_workspace
from Scout.app import build_sync_answer, INDEX_HTML, SCOUT_VERSION

sync_module = importlib.import_module("Athena.sync")

WORKSPACE_FILE = CONFIGURATION_DIR / "workspace.json"


def read_text(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.exists() else None


def restore(path: Path, content: str | None) -> None:
    if content is None:
        if path.exists():
            path.unlink()
    else:
        path.write_text(content, encoding="utf-8")


def check(name: str, condition: bool, message: str, results: list[dict]) -> None:
    results.append({"name": name, "status": "PASS" if condition else "FAIL", "message": message})


def main() -> int:
    results: list[dict] = []
    workspace_backup = read_text(WORKSPACE_FILE)
    original_pipeline = sync_module.FANTRAX_FANTASY_PIPELINE
    original_run_script = sync_module._run_script
    original_read_summary = sync_module._read_output_summary

    try:
        sync_module.FANTRAX_FANTASY_PIPELINE = [
            {
                "id": "fake_fetch",
                "label": "Fetch Fantrax data",
                "layer": "Fetch",
                "script": "fake_fetch.py",
                "requires_fetch": True,
                "validator": "fake_validator",
            }
        ]

        def fake_run_script(relative_path: str) -> Dict[str, Any]:
            raise RuntimeError("Simulated fetch failure: WARNING_NOT_LOGGED_IN")

        sync_module._run_script = fake_run_script
        sync_module._read_output_summary = lambda: {
            "canonical_transactions": 0,
            "asset_movements": 0,
            "managers_analyzed": 0,
            "market_liquidity": "unknown",
            "knowledge_readiness": None,
        }

        result = sync_module.sync(mode="fantasy_league", provider="Fantrax", fetch=True)
        op = result.get("operation_result", {})
        answer = build_sync_answer(result)
        workspace = load_workspace().get("workspace", {})

        check(
            "sync_returns_structured_operation_result",
            result.get("ok") is False and isinstance(op, dict) and op.get("success") is False,
            f"ok={result.get('ok')}; operation_success={op.get('success')}; stage={op.get('stage')}",
            results,
        )
        check(
            "failed_stage_is_visible",
            op.get("stage") == "Fetch Fantrax data" and "WARNING_NOT_LOGGED_IN" in str(op.get("reason")),
            f"stage={op.get('stage')}; reason={op.get('reason')}",
            results,
        )
        check(
            "recovery_recommendation_generated",
            "Reconnect Fantrax" in str(op.get("recommendation")),
            f"recommendation={op.get('recommendation')}",
            results,
        )
        check(
            "developer_trace_captured",
            isinstance(op.get("developer_trace"), list) and any(item.get("status") == "fail" for item in op.get("developer_trace", [])),
            f"developer_trace={op.get('developer_trace')}",
            results,
        )
        check(
            "scout_answer_surfaces_operation_result",
            answer.get("operation_result", {}).get("stage") == "Fetch Fantrax data" and "Failed stage" in answer.get("engine_conclusion", ""),
            f"title={answer.get('title')}; conclusion={answer.get('engine_conclusion')}",
            results,
        )
        history = workspace.get("operation_history")
        check(
            "operation_history_recorded",
            isinstance(history, list) and len(history) >= 1 and history[0].get("operation") == "Sync League",
            f"history_count={len(history) if isinstance(history, list) else 'not-list'}",
            results,
        )
        check(
            "scout_ui_version_and_history_panel",
            SCOUT_VERSION == "v0.5.0-drop3f2" and "Operation History" in INDEX_HTML,
            f"SCOUT_VERSION={SCOUT_VERSION}",
            results,
        )
    except Exception as exc:
        check("diagnostics_validation_unhandled_exception", False, f"Unexpected exception: {type(exc).__name__}: {exc}", results)
    finally:
        sync_module.FANTRAX_FANTASY_PIPELINE = original_pipeline
        sync_module._run_script = original_run_script
        sync_module._read_output_summary = original_read_summary
        restore(WORKSPACE_FILE, workspace_backup)

    passed = sum(1 for item in results if item["status"] == "PASS")
    failed = sum(1 for item in results if item["status"] == "FAIL")
    overall = "PASS" if failed == 0 else "FAIL"
    report_lines = [
        "Diagnostics & Recovery Validation Report",
        "========================================",
        f"Overall status: {overall}",
        f"Passed: {passed}",
        "Warnings: 0",
        f"Failed: {failed}",
        "",
    ]
    for item in results:
        report_lines.append(f"[{item['status']}] {item['name']}: {item['message']}")

    reports_dir = PROJECT_ROOT / "Reports"
    reports_dir.mkdir(exist_ok=True)
    (reports_dir / "diagnostics_recovery_validation_report.json").write_text(
        json.dumps({"overall_status": overall, "results": results}, indent=2), encoding="utf-8"
    )
    (reports_dir / "diagnostics_recovery_validation_report.txt").write_text("\n".join(report_lines), encoding="utf-8")
    print("\n".join(report_lines))
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
