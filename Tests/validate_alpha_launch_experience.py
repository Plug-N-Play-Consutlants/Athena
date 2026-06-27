"""
Validate Athena Alpha launch experience.

This validation confirms that the local alpha now has one canonical root launch
entry point and that Scout's Fantrax connection binding persists workspace state
through Athena without requiring manual JSON editing.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REPORTS_DIR = PROJECT_ROOT / "Reports"
REPORTS_DIR.mkdir(exist_ok=True)


def result(status: str, name: str, detail: str) -> Dict[str, str]:
    return {"status": status, "name": name, "detail": detail}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def validate() -> Dict[str, Any]:
    results: List[Dict[str, str]] = []

    launch_py = PROJECT_ROOT / "launch.py"
    launch_bat = PROJECT_ROOT / "launch.bat"
    scout_run = PROJECT_ROOT / "Scout" / "run_scout.py"
    scout_app = PROJECT_ROOT / "Scout" / "app.py"

    if launch_py.exists():
        text = read_text(launch_py)
        if "from Scout.run_scout import launch_scout" in text and "launch_scout(open_browser=True)" in text:
            results.append(result("PASS", "canonical_launch_py", "Root launch.py delegates to Scout.run_scout.launch_scout."))
        else:
            results.append(result("FAIL", "canonical_launch_py", "Root launch.py exists but does not delegate to the Scout launcher as expected."))
    else:
        results.append(result("FAIL", "canonical_launch_py", "Root launch.py is missing."))

    if launch_bat.exists():
        text = read_text(launch_bat).lower()
        if "python launch.py" in text:
            results.append(result("PASS", "windows_launch_bat", "launch.bat starts python launch.py from the repository root."))
        else:
            results.append(result("WARN", "windows_launch_bat", "launch.bat exists but does not clearly call python launch.py."))
    else:
        results.append(result("WARN", "windows_launch_bat", "launch.bat is missing; Spyder launch.py still works."))

    run_text = read_text(scout_run)
    if "v0.5.0-drop3f0" in run_text and "DEFAULT_PORT = 8765" in run_text:
        results.append(result("PASS", "scout_launcher_version", "Scout launcher advertises v0.5.0-drop3f0 and uses the standard local port sequence."))
    else:
        results.append(result("FAIL", "scout_launcher_version", "Scout launcher version or local port configuration is not current."))

    app_text = read_text(scout_app)
    if "def test_fantrax_connection" in app_text and "Athena.connect_fantrax" in app_text:
        results.append(result("PASS", "scout_connect_binding", "Scout Fantrax connection delegates to Athena.connect_fantrax."))
    else:
        results.append(result("FAIL", "scout_connect_binding", "Scout Fantrax connection does not clearly delegate to Athena.connect_fantrax."))

    try:
        launch_module = importlib.import_module("launch")
        if hasattr(launch_module, "launch_scout"):
            results.append(result("PASS", "launch_import", "Root launch module imports cleanly and exposes launch_scout."))
        else:
            results.append(result("FAIL", "launch_import", "Root launch module imported but launch_scout was not exposed."))
    except Exception as exc:
        results.append(result("FAIL", "launch_import", f"Root launch module failed to import: {exc}"))

    try:
        app_module = importlib.import_module("Scout.app")
        if hasattr(app_module, "test_fantrax_connection") and hasattr(app_module, "serve"):
            results.append(result("PASS", "scout_app_import", "Scout app imports cleanly with connection binding and serve entry point."))
        else:
            results.append(result("FAIL", "scout_app_import", "Scout app imported but expected functions were missing."))
    except Exception as exc:
        results.append(result("FAIL", "scout_app_import", f"Scout app failed to import: {exc}"))

    # Persistence behavior without live provider validation. This validates the
    # Athena workspace path without requiring Fantrax network/auth availability.
    workspace_path = PROJECT_ROOT / "Configuration" / "workspace.json"
    secrets_path = PROJECT_ROOT / "Configuration" / "secrets.local.json"
    old_workspace = read_text(workspace_path)
    old_secrets = read_text(secrets_path)
    try:
        import Athena
        test_league_id = "alpha_launch_validation_league"
        response = Athena.connect_fantrax(
            league_id=test_league_id,
            auth_cookie="alpha_launch_validation_cookie",
            validate=False,
            mode="fantasy_league",
        )
        saved = json.loads(read_text(workspace_path))
        workspace = saved.get("workspace", {}) if isinstance(saved, dict) else {}
        if response.get("ok") and workspace.get("league_id") == test_league_id and workspace.get("provider_key") == "fantrax":
            results.append(result("PASS", "workspace_persistence", "Athena.connect_fantrax(validate=False) persists provider and league ID to workspace.json."))
        else:
            results.append(result("FAIL", "workspace_persistence", f"Workspace persistence did not save expected provider/league values: {workspace}"))
    except Exception as exc:
        results.append(result("FAIL", "workspace_persistence", f"Workspace persistence validation failed: {exc}"))
    finally:
        if old_workspace:
            workspace_path.write_text(old_workspace, encoding="utf-8")
        if old_secrets:
            secrets_path.write_text(old_secrets, encoding="utf-8")

    passed = sum(1 for item in results if item["status"] == "PASS")
    warnings = sum(1 for item in results if item["status"] == "WARN")
    failed = sum(1 for item in results if item["status"] == "FAIL")
    overall = "PASS" if failed == 0 else "FAIL"

    return {
        "overall_status": overall,
        "passed": passed,
        "warnings": warnings,
        "failed": failed,
        "results": results,
    }


def write_reports(report: Dict[str, Any]) -> None:
    json_path = REPORTS_DIR / "alpha_launch_experience_validation_report.json"
    txt_path = REPORTS_DIR / "alpha_launch_experience_validation_report.txt"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "Alpha Launch Experience Validation Report",
        "================================================",
        f"Overall status: {report['overall_status']}",
        f"Passed: {report['passed']}",
        f"Warnings: {report['warnings']}",
        f"Failed: {report['failed']}",
        "",
    ]
    for item in report["results"]:
        lines.append(f"[{item['status']}] {item['name']}: {item['detail']}")
    lines.extend(["", f"JSON report: {json_path}", f"Text report: {txt_path}"])
    txt_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    report = validate()
    write_reports(report)
    print("Alpha Launch Experience Validation Report")
    print("================================================")
    print(f"Overall status: {report['overall_status']}")
    print(f"Passed: {report['passed']}")
    print(f"Warnings: {report['warnings']}")
    print(f"Failed: {report['failed']}")
    print("")
    for item in report["results"]:
        print(f"[{item['status']}] {item['name']}: {item['detail']}")
    print("")
    print(f"JSON report: {REPORTS_DIR / 'alpha_launch_experience_validation_report.json'}")
    print(f"Text report: {REPORTS_DIR / 'alpha_launch_experience_validation_report.txt'}")
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
