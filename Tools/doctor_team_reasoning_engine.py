"""Doctor for v0.5.0-drop4e39 Team Reasoning Engine."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    files = {
        "team_reasoning_engine": PROJECT_ROOT / "Reasoning" / "team_reasoning_engine.py",
        "public_answers": PROJECT_ROOT / "Knowledge" / "Intelligence" / "Public" / "public_answers.py",
        "team_validator": PROJECT_ROOT / "Tests" / "validate_team_reasoning_engine.py",
        "version": PROJECT_ROOT / "Core" / "version.py",
        "studio": PROJECT_ROOT / "Tools" / "athena_studio.py",
    }
    checks: list[tuple[str, bool, str]] = []
    for name, path in files.items():
        checks.append((f"{name}_exists", path.exists(), str(path)))

    engine_text = files["team_reasoning_engine"].read_text(encoding="utf-8") if files["team_reasoning_engine"].exists() else ""
    answers_text = files["public_answers"].read_text(encoding="utf-8") if files["public_answers"].exists() else ""
    version_text = files["version"].read_text(encoding="utf-8") if files["version"].exists() else ""
    studio_text = files["studio"].read_text(encoding="utf-8") if files["studio"].exists() else ""

    checks.append(("engine_class_present", "class TeamReasoningEngine" in engine_text, "Reasoning/team_reasoning_engine.py"))
    checks.append(("assessment_sections_present", all(marker in engine_text for marker in ["historical_context", "organizational_identity", "current_direction", "future_outlook"]), "Reasoning/team_reasoning_engine.py"))
    checks.append(("public_answer_uses_engine", "TeamReasoningEngine" in answers_text and "team_reasoning_assessment" in answers_text, "Knowledge/Intelligence/Public/public_answers.py"))
    checks.append(("version_is_team_reasoning_or_later", ("major.epic.sprint.patch.hotfix" in version_text or any(token in version_text for token in ["drop4e39", "drop4e40", "drop4e41", "drop4e42"])), "Core/version.py"))
    checks.append(("studio_team_buttons_registered", "Validate Team Reasoning" in studio_text and "Doctor Team Reasoning" in studio_text, "Tools/athena_studio.py"))

    failed = [item for item in checks if not item[1]]
    print("Team Reasoning Engine Doctor Report")
    print("=" * 40)
    print(f"Overall status: {'PASS' if not failed else 'FAIL'}")
    print(f"Passed: {len(checks) - len(failed)}")
    print(f"Failed: {len(failed)}")
    print()
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
