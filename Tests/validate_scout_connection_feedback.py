"""Validate Scout 3F.1 connection feedback and stale workspace handling."""

from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Scout import app


def check(name: str, condition: bool, message: str, results: list[dict]) -> None:
    results.append({"name": name, "status": "PASS" if condition else "FAIL", "message": message})


def main() -> int:
    results: list[dict] = []
    html = app.INDEX_HTML

    check(
        "version_visible",
        "Scout Alpha v0.5.0 Drop 3F.1" in html,
        "Scout UI displays the 3F.1 launch/connection feedback version.",
        results,
    )
    check(
        "connection_status_panel",
        "connectionStatus" in html and "setConnectionStatus" in html,
        "Scout has a visible connection status panel and status updater.",
        results,
    )
    check(
        "postjson_no_silent_throw",
        "data.http_status = res.status" in html and "return data" in html and "throw new Error" not in html,
        "POST helper returns failure payloads to the UI instead of throwing silently.",
        results,
    )
    check(
        "test_button_disables_and_restores",
        "button.disabled = true" in html and "button.disabled = false" in html,
        "Connection test button exposes in-progress state and restores after completion.",
        results,
    )
    check(
        "placeholder_league_ignored",
        hasattr(app, "_is_placeholder_league_id") and app._is_placeholder_league_id("test_league_id_provider_registry"),
        "Scout recognizes the provider-registry test league ID as a placeholder.",
        results,
    )
    context = app._context_payload()
    workspace = context.get("workspace", {}) if isinstance(context, dict) else {}
    check(
        "effective_league_available",
        bool(workspace.get("effective_league_id")) and workspace.get("effective_league_id") != "test_league_id_provider_registry",
        f"Effective league ID resolves to {workspace.get('effective_league_id')!r}.",
        results,
    )
    missing = app.test_fantrax_connection("")
    check(
        "missing_league_visible_failure",
        missing.get("ok") is False and bool(missing.get("message")) and bool(missing.get("error")),
        "Missing league ID returns a visible structured failure payload.",
        results,
    )

    passed = sum(1 for item in results if item["status"] == "PASS")
    failed = sum(1 for item in results if item["status"] == "FAIL")
    overall = "PASS" if failed == 0 else "FAIL"

    report_lines = [
        "Scout Connection Feedback Validation Report",
        "================================================",
        f"Overall status: {overall}",
        f"Passed: {passed}",
        f"Warnings: 0",
        f"Failed: {failed}",
        "",
    ]
    for item in results:
        report_lines.append(f"[{item['status']}] {item['name']}: {item['message']}")

    reports_dir = PROJECT_ROOT / "Reports"
    reports_dir.mkdir(exist_ok=True)
    (reports_dir / "scout_connection_feedback_validation_report.json").write_text(
        json.dumps({"overall_status": overall, "results": results}, indent=2),
        encoding="utf-8",
    )
    (reports_dir / "scout_connection_feedback_validation_report.txt").write_text("\n".join(report_lines), encoding="utf-8")
    print("\n".join(report_lines))
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
