"""Doctor for Athena 0.5.2.4.0 Event Confidence & Source Corroboration."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REQUIRED_FILES = [
    "Engine/EventConfidence/__init__.py",
    "Engine/EventConfidence/confidence_models.py",
    "Engine/EventConfidence/source_profiles.py",
    "Engine/EventConfidence/corroboration.py",
    "Engine/EventConfidence/confidence_engine.py",
    "Tests/validate_event_confidence_source_corroboration.py",
    "Tools/doctor_event_confidence_source_corroboration.py",
]
REQUIRED_EXPORTS = {
    "EventConfidenceEngine",
    "score_event_confidence",
    "EventConfidenceResult",
    "SourceCorroborationResult",
    "scout_confidence_payload",
}


def report(name: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))
    return ok


def exports_from_init() -> set[str]:
    init_file = PROJECT_ROOT / "Engine" / "EventConfidence" / "__init__.py"
    tree = ast.parse(init_file.read_text(encoding="utf-8"))
    exports: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__" and isinstance(node.value, ast.List):
                    for item in node.value.elts:
                        if isinstance(item, ast.Constant) and isinstance(item.value, str):
                            exports.add(item.value)
    return exports


def _version_tuple(value: str) -> tuple[int, int, int, int, int]:
    parts = str(value).split(".")
    numeric = []
    for part in parts[:5]:
        try:
            numeric.append(int(part))
        except ValueError:
            numeric.append(0)
    while len(numeric) < 5:
        numeric.append(0)
    return tuple(numeric)  # type: ignore[return-value]

def _version_at_least(value: str, minimum: str) -> bool:
    return _version_tuple(value) >= _version_tuple(minimum)


def main() -> int:
    print("Event Confidence & Source Corroboration Doctor")
    print("=" * 64)
    checks: list[bool] = []

    for rel in REQUIRED_FILES:
        checks.append(report(f"required file exists: {rel}", (PROJECT_ROOT / rel).exists(), rel))

    from Core.version import ATHENA_VERSION, ATHENA_BUILD, RELEASE_NAME
    checks.append(report("version metadata is 0.5.2.4.0 or later", _version_at_least(ATHENA_VERSION, "0.5.2.4.0") and ATHENA_BUILD == ATHENA_VERSION, ATHENA_VERSION))
    checks.append(report("release name is available", bool(RELEASE_NAME), RELEASE_NAME))

    exports = exports_from_init()
    checks.append(report("EventConfidence exports canonical symbols", REQUIRED_EXPORTS.issubset(exports), ", ".join(sorted(exports))))

    from Engine.EventConfidence import EventConfidenceEngine, scout_confidence_payload
    from Knowledge.Events import normalize_event_payload

    event = normalize_event_payload({
        "event_id": "doctor_conf_001",
        "event_type": "trade",
        "sport": "nhl",
        "subject": "Doctor Player",
        "summary": "Doctor Player was traded.",
        "source_id": "nhl_api",
        "published_at": "2026-06-23T12:00:00+00:00",
        "source_confidence": 0.94,
    })
    result = EventConfidenceEngine().score_events([event])
    payload = scout_confidence_payload(result.results[0]) if result.results else {}
    checks.append(report("engine scores doctor sample event", result.result_count == 1 and payload.get("confidence_score", 0) >= 70, str(payload)))

    print("-" * 64)
    passed = sum(1 for item in checks if item)
    failed = len(checks) - passed
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("Overall status:", "PASS" if failed == 0 else "FAIL")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
