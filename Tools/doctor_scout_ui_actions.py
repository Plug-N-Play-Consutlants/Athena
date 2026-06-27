"""Static doctor for Scout UI action wiring."""
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main():
    print("Scout UI Actions Doctor")
    print("=======================")

    app_path = PROJECT_ROOT / "Scout" / "app.py"
    repair_path = PROJECT_ROOT / "Scout" / "ui_action_repair.js"
    text = app_path.read_text(encoding="utf-8") if app_path.exists() else ""

    checks = [
        ("Scout app exists", app_path.exists()),
        ("Repair JS exists", repair_path.exists()),
        ("Question field exists", 'id="question"' in text),
        ("Ask API likely exists", "/api/ask" in text or "api/ask" in text or "do_POST" in text),
        ("No prefilled old question", ">Who are the most active managers?</textarea>" not in text),
    ]

    # App may not yet reference the repair JS; if not, user can use the inline patch below.
    references_repair = "ui_action_repair.js" in text
    checks.append(("App references repair JS", references_repair))

    for label, ok in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")

    if not references_repair:
        print()
        print("Repair JS is present but not referenced by Scout/app.py.")
        print("Use Tools/patch_scout_app_for_ui_actions.py once, then relaunch Scout.")

    if not all(ok for _, ok in checks[:-1]):
        raise RuntimeError("Scout UI action prerequisites failed.")

    print()
    print("STATUS:", "PASS" if references_repair else "NEEDS APP PATCH")


if __name__ == "__main__":
    main()
