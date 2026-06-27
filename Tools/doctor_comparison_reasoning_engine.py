"""Doctor for v0.5.0-drop4e40 Comparison Intelligence Engine."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    files = {
        "comparison_reasoning_engine": PROJECT_ROOT / "Reasoning" / "comparison_reasoning_engine.py",
        "public_answers": PROJECT_ROOT / "Knowledge" / "Intelligence" / "Public" / "public_answers.py",
        "request_router": PROJECT_ROOT / "Knowledge" / "Intelligence" / "Routing" / "request_router.py",
        "scout_router": PROJECT_ROOT / "Scout" / "conversation" / "router.py",
        "comparison_validator": PROJECT_ROOT / "Tests" / "validate_comparison_reasoning_engine.py",
        "version": PROJECT_ROOT / "Core" / "version.py",
        "studio": PROJECT_ROOT / "Tools" / "athena_studio.py",
    }
    checks: list[tuple[str, bool, str]] = []
    for name, path in files.items():
        checks.append((f"{name}_exists", path.exists(), str(path)))

    engine_text = files["comparison_reasoning_engine"].read_text(encoding="utf-8") if files["comparison_reasoning_engine"].exists() else ""
    answers_text = files["public_answers"].read_text(encoding="utf-8") if files["public_answers"].exists() else ""
    request_text = files["request_router"].read_text(encoding="utf-8") if files["request_router"].exists() else ""
    scout_text = files["scout_router"].read_text(encoding="utf-8") if files["scout_router"].exists() else ""
    version_text = files["version"].read_text(encoding="utf-8") if files["version"].exists() else ""
    studio_text = files["studio"].read_text(encoding="utf-8") if files["studio"].exists() else ""

    checks.append(("engine_class_present", "class ComparisonReasoningEngine" in engine_text, "Reasoning/comparison_reasoning_engine.py"))
    checks.append(("assessment_sections_present", all(marker in engine_text for marker in ["executive_comparison", "historical_comparison", "prime_comparison", "future_outlook", "athena_conclusion"]), "Reasoning/comparison_reasoning_engine.py"))
    checks.append(("public_player_answer_uses_engine", "ComparisonReasoningEngine" in answers_text and "comparison_assessment" in answers_text, "Knowledge/Intelligence/Public/public_answers.py"))
    checks.append(("public_team_comparison_answer_present", "def team_comparison_answer" in answers_text, "Knowledge/Intelligence/Public/public_answers.py"))
    checks.append(("request_router_team_comparison_route", "team_comparison" in request_text and "TEAM_COMPARISON" in request_text, "Knowledge/Intelligence/Routing/request_router.py"))
    checks.append(("scout_router_team_comparison_bound", "team_comparison_answer" in scout_text, "Scout/conversation/router.py"))
    checks.append(("version_is_comparison_or_later", ("major.epic.sprint.patch.hotfix" in version_text or any(token in version_text for token in ["drop4e39", "drop4e40", "drop4e41", "drop4e42"])), "Core/version.py"))
    checks.append(("studio_comparison_buttons_registered", "Validate Comparison" in studio_text and "Doctor Comparison" in studio_text, "Tools/athena_studio.py"))

    failed = [item for item in checks if not item[1]]
    print("Comparison Intelligence Engine Doctor Report")
    print("=" * 48)
    print(f"Overall status: {'PASS' if not failed else 'FAIL'}")
    print(f"Passed: {len(checks) - len(failed)}")
    print(f"Failed: {len(failed)}")
    print()
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
