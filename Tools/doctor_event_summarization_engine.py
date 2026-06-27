"""Doctor for Athena 0.5.2.5.0 Event Summarization Engine."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REQUIRED_FILES = [
    "Engine/EventSummarization/__init__.py",
    "Engine/EventSummarization/summary_models.py",
    "Engine/EventSummarization/summary_engine.py",
    "Tests/validate_event_summarization_engine.py",
    "Tools/doctor_event_summarization_engine.py",
]
REQUIRED_EXPORTS = {
    "EventSummarizationEngine",
    "EventSummaryBatch",
    "EventExecutiveBrief",
    "EventSummaryItem",
    "summarize_events",
    "scout_event_summary_payload",
}


def report(name: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))
    return ok


def exports_from_init() -> set[str]:
    init_file = PROJECT_ROOT / "Engine" / "EventSummarization" / "__init__.py"
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


def main() -> int:
    print("Event Summarization Engine Doctor")
    print("=" * 64)
    checks: list[bool] = []

    for rel in REQUIRED_FILES:
        checks.append(report(f"required file exists: {rel}", (PROJECT_ROOT / rel).exists(), rel))

    from Core.version import ATHENA_VERSION, ATHENA_BUILD, RELEASE_NAME
    checks.append(report("version metadata is 0.5.2.5.0 or later", ATHENA_VERSION >= "0.5.2.5.0" and ATHENA_BUILD == ATHENA_VERSION, ATHENA_VERSION))
    checks.append(report("release name is present", bool(RELEASE_NAME), RELEASE_NAME))

    exports = exports_from_init()
    checks.append(report("EventSummarization exports canonical symbols", REQUIRED_EXPORTS.issubset(exports), ", ".join(sorted(exports))))

    from Engine.EventSummarization import EventSummarizationEngine
    from Knowledge.Events import normalize_event_payload
    event = normalize_event_payload({
        "event_id": "doctor_summary_001",
        "event_type": "signing",
        "sport": "nhl",
        "league": "nhl",
        "subject": "Doctor Club",
        "summary": "Doctor Club signed a depth forward.",
        "source_id": "nhl_api",
        "source_confidence": 0.90,
    })
    batch = EventSummarizationEngine().summarize_events([event])
    checks.append(report("engine builds doctor sample brief", batch.brief.item_count == 1 and bool(batch.scout_payload.get("executive_summary")), str(batch.brief.to_dict())))

    print("-" * 64)
    passed = sum(1 for item in checks if item)
    failed = len(checks) - passed
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("Overall status:", "PASS" if failed == 0 else "FAIL")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
