from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Spyder keeps modules loaded between runfile calls. Clear Athena/provider modules
# so this validator checks the files on disk, not stale imports from memory.
for module_name in list(sys.modules):
    if (
        module_name == "Athena"
        or module_name.startswith("Athena.")
        or module_name == "Providers.base"
        or module_name.startswith("Providers.base.")
        or module_name == "Providers.Fantrax.fantrax_provider"
    ):
        sys.modules.pop(module_name, None)

from Core.json_utils import write_json  # noqa: E402
from Core.logger import log, log_header  # noqa: E402
from Core.project_paths import REPORTS_DIR  # noqa: E402

REPORT_JSON = REPORTS_DIR / "athena_provider_registry_connect_validation_report.json"
REPORT_TXT = REPORTS_DIR / "athena_provider_registry_connect_validation_report.txt"


def check(name: str, fn):
    try:
        details = fn()
        return {"name": name, "status": "pass", "message": details.get("message", "passed"), "details": details}
    except Exception as exc:  # noqa: BLE001 - validation boundary
        return {"name": name, "status": "fail", "message": str(exc), "details": {}}


def validate_imports():
    import Athena
    from Providers.base.registry import registered_providers

    assert Athena.__version__ == "0.5.0-drop3e3", Athena.__version__
    providers = registered_providers()
    assert "fantrax" in providers, providers
    return {"message": f"Athena {Athena.__version__}; registered providers: {providers}", "providers": providers}


def validate_status_provider_registry():
    import Athena

    status = Athena.status()
    assert status.get("athena_version") == "0.5.0-drop3e3", status.get("athena_version")
    assert "registered_providers" in status, status
    assert "fantrax" in status.get("registered_providers", []), status.get("registered_providers")
    assert "active_provider" in status, status
    return {
        "message": "Athena status exposes provider registry and active provider status.",
        "registered_providers": status.get("registered_providers"),
        "active_provider": status.get("active_provider"),
    }


def validate_connect_without_validation_uses_registry():
    import Athena

    result = Athena.connect(
        provider="fantrax",
        league_id="test_league_id_provider_registry",
        auth_cookie="",
        validate=False,
        mode="fantasy_league",
    )
    assert result.get("ok") is True, result
    assert result.get("provider_key") == "fantrax", result
    assert "registered_providers" in result, result
    assert "provider_status" in result, result
    workspace = Athena.workspace().get("workspace", {})
    assert workspace.get("provider_key") == "fantrax", workspace
    assert workspace.get("league_id") == "test_league_id_provider_registry", workspace
    return {
        "message": "Athena connect(validate=False) resolved Fantrax through provider registry.",
        "provider_status": result.get("provider_status"),
        "workspace_provider_key": workspace.get("provider_key"),
    }


def validate_no_direct_fantrax_client_import_in_athena_connect():
    source = (PROJECT_ROOT / "Athena" / "connect.py").read_text(encoding="utf-8")
    forbidden = "from Providers.Fantrax.fantrax_client import FantraxClient"
    assert forbidden not in source, "Athena.connect imports FantraxClient directly."
    assert "get_provider" in source, "Athena.connect does not use provider registry."
    return {"message": "Athena.connect uses provider registry rather than direct FantraxClient import."}


def validate_fantrax_provider_still_imports():
    from Providers.Fantrax.fantrax_provider import FantraxProvider
    from Providers.base.provider import BaseProvider

    provider = FantraxProvider()
    assert isinstance(provider, BaseProvider)
    return {"message": "FantraxProvider still imports and implements BaseProvider."}


def validate_sync_still_imports():
    import Athena

    dry_run = Athena.sync(dry_run=True, fetch=False)
    assert dry_run.get("ok") is True, dry_run
    assert dry_run.get("dry_run") is True, dry_run
    return {"message": "Athena sync dry-run still imports after registry connect changes.", "steps": len(dry_run.get("planned_steps", []))}


def main():
    log_header("ATHENA PROVIDER REGISTRY CONNECT VALIDATION")
    checks = [
        check("imports_and_registry", validate_imports),
        check("status_provider_registry", validate_status_provider_registry),
        check("connect_without_validation_uses_registry", validate_connect_without_validation_uses_registry),
        check("no_direct_fantrax_client_import", validate_no_direct_fantrax_client_import_in_athena_connect),
        check("fantrax_provider_still_imports", validate_fantrax_provider_still_imports),
        check("sync_still_imports", validate_sync_still_imports),
    ]

    passed = sum(1 for item in checks if item["status"] == "pass")
    failed = sum(1 for item in checks if item["status"] == "fail")
    report = {
        "report_name": "Athena Provider Registry Connect Validation",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": "pass" if failed == 0 else "fail",
        "summary": {"pass": passed, "fail": failed},
        "checks": checks,
    }
    write_json(REPORT_JSON, report)

    lines = [
        "Athena Provider Registry Connect Validation Report",
        "=" * 56,
        f"Overall status: {report['overall_status'].upper()}",
        f"Passed: {passed}",
        f"Failed: {failed}",
        "",
    ]
    for item in checks:
        lines.append(f"[{item['status'].upper()}] {item['name']}: {item['message']}")
    REPORT_TXT.write_text("\n".join(lines), encoding="utf-8")
    for line in lines:
        log(line)
    log("")
    log(f"JSON report: {REPORT_JSON}")
    log(f"Text report: {REPORT_TXT}")


if __name__ == "__main__":
    main()
