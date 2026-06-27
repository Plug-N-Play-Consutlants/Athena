from pathlib import Path
import sys
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.json_utils import write_json
from Core.logger import log_header, log
from Core.project_paths import REPORTS_DIR

# Spyder keeps imported modules in the active kernel between runfile() calls.
# Purge Athena before validation so this test reflects the files currently on disk.
for module_name in list(sys.modules):
    if module_name == "Athena" or module_name.startswith("Athena."):
        del sys.modules[module_name]

import Athena

REPORT_JSON = REPORTS_DIR / "athena_sync_validation_report.json"
REPORT_TXT = REPORTS_DIR / "athena_sync_validation_report.txt"


def result(name, status, message, details=None):
    return {
        "name": name,
        "status": status,
        "message": message,
        "details": details or {},
    }


def validate():
    checks = []

    try:
        status = Athena.status()
        version = status.get("athena_version")
        checks.append(result(
            "athena_status_version",
            "pass" if version == "0.5.0-drop3d" else "fail",
            f"Athena version: {version}",
            status,
        ))
    except Exception as exc:
        checks.append(result("athena_status_version", "fail", str(exc)))

    try:
        dry = Athena.sync(mode="fantasy_league", provider="Fantrax", fetch=True, dry_run=True)
        planned = dry.get("planned_steps", []) if isinstance(dry, dict) else []
        fetch_steps = [step for step in planned if step.get("layer") == "Fetch"]
        validators = [step.get("validator") for step in planned if step.get("validator")]
        checks.append(result(
            "sync_dry_run_fetch_plan",
            "pass" if dry.get("ok") and planned and fetch_steps and validators else "fail",
            f"Dry run planned {len(planned)} steps including {len(fetch_steps)} fetch step(s) and {len(validators)} validators.",
            {"planned_steps": planned},
        ))
    except Exception as exc:
        checks.append(result("sync_dry_run_fetch_plan", "fail", str(exc)))

    try:
        dry = Athena.sync(mode="fantasy_league", provider="Fantrax", fetch=False, dry_run=True)
        planned = dry.get("planned_steps", []) if isinstance(dry, dict) else []
        fetch_steps = [step for step in planned if step.get("layer") == "Fetch"]
        checks.append(result(
            "sync_dry_run_rebuild_plan",
            "pass" if dry.get("ok") and planned and not fetch_steps else "fail",
            f"Dry run planned {len(planned)} rebuild steps and skipped live fetch.",
            {"planned_steps": planned},
        ))
    except Exception as exc:
        checks.append(result("sync_dry_run_rebuild_plan", "fail", str(exc)))

    try:
        workspace = Athena.workspace().get("workspace", {})
        checks.append(result(
            "workspace_sync_fields",
            "pass" if "last_sync_at" in workspace and "last_sync_status" in workspace else "fail",
            "Workspace exposes sync tracking fields.",
            workspace,
        ))
    except Exception as exc:
        checks.append(result("workspace_sync_fields", "fail", str(exc)))

    try:
        from Athena.sync import FANTRAX_FANTASY_PIPELINE
        layers = {step.get("layer") for step in FANTRAX_FANTASY_PIPELINE}
        scripts = [step.get("script") for step in FANTRAX_FANTASY_PIPELINE]
        expected = {
            "Providers/Fantrax/build/transaction_master.py",
            "Knowledge/transaction_history.py",
            "Intelligence/manager_behavior.py",
            "Intelligence/league_market.py",
        }
        checks.append(result(
            "pipeline_layers_and_scripts",
            "pass" if {"Fetch", "Build", "Knowledge", "Intelligence"}.issubset(layers) and expected.issubset(set(scripts)) else "fail",
            f"Pipeline layers: {sorted(layers)}",
            {"scripts": scripts},
        ))
    except Exception as exc:
        checks.append(result("pipeline_layers_and_scripts", "fail", str(exc)))

    try:
        dry = Athena.sync(mode="fantasy_league", provider="Fantrax", dry_run=True)
        checks.append(result(
            "sync_public_api",
            "pass" if isinstance(dry, dict) and dry.get("ok") else "fail",
            "athena.sync() returned a structured sync response.",
        ))
    except Exception as exc:
        checks.append(result("sync_public_api", "fail", str(exc)))

    return checks


def main():
    log_header("ATHENA SYNC VALIDATION")
    checks = validate()
    passed = sum(1 for check in checks if check["status"] == "pass")
    failed = sum(1 for check in checks if check["status"] == "fail")

    report = {
        "report_name": "Athena Sync Validation",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": "pass" if failed == 0 else "fail",
        "summary": {"pass": passed, "fail": failed},
        "checks": checks,
    }
    write_json(REPORT_JSON, report)

    lines = [
        "Athena Sync Validation Report",
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
