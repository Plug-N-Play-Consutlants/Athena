from pathlib import Path
import sys
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.json_utils import write_json
from Core.logger import log, log_header
from Core.project_paths import REPORTS_DIR
from Diagnostics import start_trace
from Providers.base import (
    BaseProvider,
    ConnectionState,
    ProviderRegistry,
    ProviderSessionStatus,
    provider_event,
)

REPORT_JSON = REPORTS_DIR / "provider_foundation_validation_report.json"
REPORT_TXT = REPORTS_DIR / "provider_foundation_validation_report.txt"


def result(name, status, message, details=None):
    return {
        "name": name,
        "status": status,
        "message": message,
        "details": details or {},
    }


class DummyProvider(BaseProvider):
    provider_key = "dummy"
    provider_name = "Dummy Provider"

    def connect(self, **kwargs):
        return {"ok": True, "kwargs": kwargs}

    def disconnect(self):
        return {"ok": True}

    def test(self, **kwargs):
        return {"ok": True}

    def status(self):
        return ProviderSessionStatus(
            provider=self.provider_name,
            state=ConnectionState.CONNECTED,
            authenticated=True,
            secret_present=False,
            message="Dummy provider connected.",
        )

    def fetch(self, endpoint, **kwargs):
        return {"endpoint": endpoint, "kwargs": kwargs}


def validate():
    checks = []

    try:
        states = [state.value for state in ConnectionState]
        checks.append(result(
            "connection_states",
            "pass" if "connected" in states and "expired" in states else "fail",
            f"Connection states available: {states}",
        ))
    except Exception as exc:
        checks.append(result("connection_states", "fail", str(exc)))

    try:
        event = provider_event(
            provider="Dummy",
            operation="connect",
            status="success",
            message="Connection succeeded.",
            trace_id="trace-test",
            step="test",
        )
        checks.append(result(
            "provider_event_shape",
            "pass" if event.get("trace_id") == "trace-test" and event.get("status") == "success" else "fail",
            "Provider event is serializable.",
            event,
        ))
    except Exception as exc:
        checks.append(result("provider_event_shape", "fail", str(exc)))

    try:
        registry = ProviderRegistry()
        registry.register("dummy", DummyProvider)
        provider = registry.get("dummy")
        status = provider.status().to_dict()
        checks.append(result(
            "provider_registry",
            "pass" if provider.provider_key == "dummy" and status.get("authenticated") else "fail",
            "Provider registry can register and instantiate a provider.",
            {"registered": registry.keys(), "status": status},
        ))
    except Exception as exc:
        checks.append(result("provider_registry", "fail", str(exc)))

    try:
        recorder = start_trace("provider_foundation_validation")
        recorder.emit(component="provider", step="import", status="success", message="Provider foundation imported.")
        summary = recorder.summary()
        checks.append(result(
            "diagnostics_trace",
            "pass" if summary.get("event_count") == 1 and summary.get("trace_id") else "fail",
            "Diagnostics recorder produced a trace summary.",
            summary,
        ))
    except Exception as exc:
        checks.append(result("diagnostics_trace", "fail", str(exc)))

    try:
        import Athena  # noqa: F401
        checks.append(result("athena_still_imports", "pass", "Athena still imports after provider foundation addition."))
    except Exception as exc:
        checks.append(result("athena_still_imports", "fail", str(exc)))

    try:
        from Providers.Fantrax.fantrax_client import FantraxClient  # noqa: F401
        checks.append(result("fantrax_client_still_imports", "pass", "FantraxClient still imports unchanged."))
    except Exception as exc:
        checks.append(result("fantrax_client_still_imports", "fail", str(exc)))

    return checks


def main():
    log_header("PROVIDER FOUNDATION VALIDATION")
    checks = validate()
    passed = sum(1 for check in checks if check["status"] == "pass")
    failed = sum(1 for check in checks if check["status"] == "fail")

    report = {
        "report_name": "Provider Foundation Validation",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": "pass" if failed == 0 else "fail",
        "summary": {"pass": passed, "fail": failed},
        "checks": checks,
    }
    write_json(REPORT_JSON, report)

    lines = [
        "Provider Foundation Validation Report",
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
