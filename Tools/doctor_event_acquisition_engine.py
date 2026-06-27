"""Doctor for Athena 0.5.1.3.0 Event Acquisition Engine."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check(name: str, ok: bool, detail: str = "") -> tuple[str, bool, str]:
    return (name, bool(ok), detail)


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    version_file = ROOT / "Core" / "version.py"
    version_text = version_file.read_text(encoding="utf-8") if version_file.exists() else ""
    checks.append(check("version is 0.5.1.3.0 or later", 'VERSION_SCHEMA = "major.epic.sprint.patch.hotfix"' in version_text and ('ATHENA_VERSION = "0.5.1.3.0"' in version_text or 'ATHENA_VERSION = "0.5.1.4.' in version_text or 'ATHENA_VERSION = "0.5.1.5.' in version_text or 'ATHENA_VERSION = "0.5.2.' in version_text), str(version_file)))

    required = [
        "Knowledge/Events/feeds.py",
        "Knowledge/Events/connectors.py",
        "Knowledge/Events/acquisition.py",
        "Tests/validate_event_acquisition_engine.py",
        "Tools/doctor_event_acquisition_engine.py",
    ]
    for rel in required:
        checks.append(check(f"required file exists: {rel}", (ROOT / rel).exists(), rel))

    try:
        feeds = importlib.import_module("Knowledge.Events.feeds")
        connectors = importlib.import_module("Knowledge.Events.connectors")
        acquisition = importlib.import_module("Knowledge.Events.acquisition")
        registry = feeds.seed_feed_registry()
        summary = registry.health_summary()
        checks.append(check("feed registry seeds feeds", summary.get("feed_count", 0) >= 6, str(summary)))
        checks.append(check("connector registry exposes expected types", {"rss", "rest_api", "json_feed", "static_file", "provider_adapter"}.issubset(set(connectors.CONNECTOR_CLASSES)), str(connectors.connector_registry_summary())))
        engine = acquisition.EventAcquisitionEngine(registry)
        plan = engine.scheduler.plan_on_demand(sport="nhl", league="nhl")
        checks.append(check("scheduler produces NHL on-demand plan", bool(plan.feed_ids), str(plan.to_dict())))
        result = engine.run_feed("static_event_import", payload=acquisition.demo_static_payload())
        checks.append(check("static feed run produces canonical event", result.ok() and len(result.events) == 1 and result.events[0].event_type == "trade", str(result.to_dict())))
    except Exception as exc:
        checks.append(check("event acquisition imports and smoke test", False, repr(exc)))

    print("Event Acquisition Engine Doctor")
    print("=" * 64)
    failed = 0
    for name, ok, detail in checks:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}: {detail}")
        if not ok:
            failed += 1
    print(f"\nOverall status: {'PASS' if failed == 0 else 'FAIL'}")
    if failed:
        print(f"Failed: {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
