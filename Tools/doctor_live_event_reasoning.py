"""Doctor for Athena 0.5.2.1.1 Live Event Reasoning."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CHECKS: list[tuple[str, bool, str]] = []


def _version_tuple(value: str) -> tuple[int, int, int, int, int]:
    parts = str(value).split(".")
    if len(parts) != 5 or not all(part.isdigit() for part in parts):
        return (0, 0, 0, 0, 0)
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def _version_at_least(value: str, minimum: str) -> bool:
    return _version_tuple(value) >= _version_tuple(minimum)


def check(name: str, condition: bool, detail: str) -> None:
    CHECKS.append((name, bool(condition), detail))


def main() -> int:
    expected = [
        ROOT / "Engine" / "EventReasoning" / "__init__.py",
        ROOT / "Engine" / "EventReasoning" / "models.py",
        ROOT / "Engine" / "EventReasoning" / "classifier.py",
        ROOT / "Engine" / "EventReasoning" / "impact.py",
        ROOT / "Engine" / "EventReasoning" / "reasoning_engine.py",
        ROOT / "Engine" / "Events" / "facade.py",
        ROOT / "Knowledge" / "Events" / "models.py",
        ROOT / "Tests" / "validate_live_event_reasoning.py",
    ]
    for path in expected:
        check(path.name, path.exists(), str(path.relative_to(ROOT)))

    try:
        version = importlib.import_module("Core.version")
        check("version_metadata", _version_at_least(getattr(version, "ATHENA_VERSION", ""), "0.5.2.1.0"), getattr(version, "ATHENA_VERSION", "missing"))
        check("release_name", bool(getattr(version, "RELEASE_NAME", "")), getattr(version, "RELEASE_NAME", "missing"))
    except Exception as exc:
        check("version_import", False, repr(exc))

    try:
        mod = importlib.import_module("Engine.EventReasoning")
        check("engine_import", hasattr(mod, "EventReasoningEngine"), "Engine.EventReasoning exports EventReasoningEngine")
        check("reason_about_events_export", hasattr(mod, "reason_about_events"), "Engine.EventReasoning exports reason_about_events")
    except Exception as exc:
        check("engine_import", False, repr(exc))

    try:
        facade = importlib.import_module("Engine.Events.facade")
        check("facade_version", _version_at_least(getattr(facade, "EVENT_ENGINE_VERSION", ""), "0.5.2.1.0"), getattr(facade, "EVENT_ENGINE_VERSION", "missing"))
        check("facade_reason_method", hasattr(facade.EventEngineFacade, "reason"), "EventEngineFacade.reason available")
        check("facade_acquire_reason_method", hasattr(facade.EventEngineFacade, "acquire_and_reason"), "EventEngineFacade.acquire_and_reason available")
    except Exception as exc:
        check("facade_import", False, repr(exc))

    print("Live Event Reasoning Doctor")
    print("=" * 56)
    failures = 0
    for name, ok, detail in CHECKS:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
        failures += 0 if ok else 1
    print()
    print(f"Overall status: {'PASS' if failures == 0 else 'FAIL'}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
