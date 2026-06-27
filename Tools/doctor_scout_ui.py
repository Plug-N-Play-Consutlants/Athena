"""Doctor for Scout UI prompt behavior."""
from __future__ import annotations

from pathlib import Path
import re
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main():
    print("Scout UI Doctor")
    print("===============")

    app_path = PROJECT_ROOT / "Scout" / "app.py"
    text = app_path.read_text(encoding="utf-8")

    textarea_match = re.search(r'<textarea[^>]*id="question"[^>]*>(.*?)</textarea>', text, re.S)
    value = textarea_match.group(1).strip() if textarea_match else None

    checks = [
        ("Scout app exists", app_path.exists()),
        ("Question textarea exists", textarea_match is not None),
        ("Question textarea is not prefilled", value == ""),
        ("Question placeholder exists", "placeholder=" in textarea_match.group(0) if textarea_match else False),
    ]

    for label, ok in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")

    print()
    print("Question textarea content:", repr(value))

    if not all(ok for _, ok in checks):
        raise RuntimeError("Scout UI doctor failed.")

    print()
    print("STATUS: PASS")


if __name__ == "__main__":
    main()
