from pathlib import Path
import json
import sys
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.json_utils import write_json
from Core.logger import log_header, log
from Core.project_paths import REPORTS_DIR

REPORT_JSON = REPORTS_DIR / "fantrax_provider_adapter_validation_report.json"
REPORT_TXT = REPORTS_DIR / "fantrax_provider_adapter_validation_report.txt"


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
        from Providers.base import registered_providers, get_provider
        providers = registered_providers()
        checks.append(result(
            "registry_import",
            "pass" if "fantrax" in providers else "fail",
            f"Registered providers: {providers}",
            {"providers": providers},
        ))
    except Exception as exc:
        checks.append(result("registry_import", "fail", str(exc)))
        return checks

    try:
        provider = get_provider("fantrax")
        checks.append(result(
            "fantrax_provider_instance",
            "pass" if provider.__class__.__name__ == "FantraxProvider" else "fail",
            f"Provider instance: {provider.__class__.__name__}",
        ))
    except Exception as exc:
        checks.append(result("fantrax_provider_instance", "fail", str(exc)))
        return checks

    try:
        from Providers.base.provider import BaseProvider
        checks.append(result(
            "fantrax_provider_contract",
            "pass" if isinstance(provider, BaseProvider) else "fail",
            "FantraxProvider implements BaseProvider." if isinstance(provider, BaseProvider) else "FantraxProvider does not implement BaseProvider.",
        ))
    except Exception as exc:
        checks.append(result("fantrax_provider_contract", "fail", str(exc)))

    try:
        status = provider.status().to_dict()
        json.dumps(status)
        checks.append(result(
            "fantrax_status_shape",
            "pass" if status.get("provider") == "Fantrax" else "fail",
            "Fantrax provider status is JSON-safe.",
            status,
        ))
    except Exception as exc:
        checks.append(result("fantrax_status_shape", "fail", str(exc)))

    try:
        from Providers.Fantrax.fantrax_client import FantraxClient
        checks.append(result(
            "fantrax_client_still_imports",
            "pass" if FantraxClient else "fail",
            "Existing FantraxClient still imports unchanged.",
        ))
    except Exception as exc:
        checks.append(result("fantrax_client_still_imports", "fail", str(exc)))

    try:
        import Athena
        status = Athena.status()
        checks.append(result(
            "athena_still_imports",
            "pass" if isinstance(status, dict) else "fail",
            "Athena still imports after Fantrax provider adapter addition.",
            {"athena_version": status.get("athena_version") if isinstance(status, dict) else None},
        ))
    except Exception as exc:
        checks.append(result("athena_still_imports", "fail", str(exc)))

    try:
        fetch_method = getattr(provider, "fetch", None)
        connect_method = getattr(provider, "connect", None)
        checks.append(result(
            "provider_public_methods",
            "pass" if callable(fetch_method) and callable(connect_method) else "fail",
            "FantraxProvider exposes provider public methods.",
            {"connect": callable(connect_method), "fetch": callable(fetch_method)},
        ))
    except Exception as exc:
        checks.append(result("provider_public_methods", "fail", str(exc)))

    return checks


def main():
    log_header("FANTRAX PROVIDER ADAPTER VALIDATION")

    checks = validate()
    passed = sum(1 for c in checks if c["status"] == "pass")
    failed = sum(1 for c in checks if c["status"] == "fail")

    report = {
        "report_name": "Fantrax Provider Adapter Validation",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": "pass" if failed == 0 else "fail",
        "summary": {"pass": passed, "fail": failed},
        "checks": checks,
    }

    write_json(REPORT_JSON, report)

    lines = [
        "Fantrax Provider Adapter Validation Report",
        "=" * 48,
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
