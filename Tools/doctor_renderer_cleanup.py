"""Doctor for v0.5.0-drop4e38 renderer cleanup."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    app = PROJECT_ROOT / "Scout" / "app.py"
    executive = PROJECT_ROOT / "Reasoning" / "composition" / "executive_brief.py"
    public_answers = PROJECT_ROOT / "Knowledge" / "Intelligence" / "Public" / "public_answers.py"
    validator = PROJECT_ROOT / "Tests" / "validate_renderer_cleanup.py"

    checks.append(("scout_app_exists", app.exists(), str(app)))
    checks.append(("executive_brief_exists", executive.exists(), str(executive)))
    checks.append(("public_answers_exists", public_answers.exists(), str(public_answers)))
    checks.append(("renderer_validator_exists", validator.exists(), str(validator)))

    app_text = app.read_text(encoding="utf-8") if app.exists() else ""
    exec_text = executive.read_text(encoding="utf-8") if executive.exists() else ""
    public_text = public_answers.read_text(encoding="utf-8") if public_answers.exists() else ""

    checks.append(("frontend_redundant_conclusion_guard", "conclusionIsRedundant" in app_text, "Scout/app.py"))
    checks.append(("brief_body_does_not_start_with_title", "Scout already renders the title" in exec_text, "Reasoning/composition/executive_brief.py"))
    checks.append(("public_context_replacements", "fantasy evidence" in public_text and "Context evidence" in public_text, "Knowledge/Intelligence/Public/public_answers.py"))
    checks.append(("public_comparison_fantasy_skip_card", '{"label": "Fantasy", "value": "skipped"}' in public_text, "Knowledge/Intelligence/Public/public_answers.py"))

    failed = [item for item in checks if not item[1]]
    print("Renderer Cleanup Doctor Report")
    print("=" * 32)
    print(f"Overall status: {'PASS' if not failed else 'FAIL'}")
    print(f"Passed: {len(checks) - len(failed)}")
    print(f"Failed: {len(failed)}")
    print()
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
