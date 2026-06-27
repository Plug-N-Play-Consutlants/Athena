"""Doctor for Athena Studio toolbar refinement.

Hotfix 0.5.1.1.1: keep output ASCII-safe for Windows console/log
capture while still checking Unicode toolbar labels in the source text.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT / "Tools" / "athena_studio.py"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _safe_label(value: str) -> str:
    """Return a console-safe diagnostic label for Unicode UI markers."""
    return value.encode("unicode_escape").decode("ascii")


def main() -> int:
    print("Athena Studio Toolbar Doctor")
    print("=" * 60)
    failures: list[str] = []
    if not STUDIO.exists():
        print("[FAIL] Tools/athena_studio.py missing")
        return 1
    text = STUDIO.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        print(f"[FAIL] Studio syntax error: {exc}")
        return 1
    methods = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    for method in ["_toolbar_button", "_button_group", "refresh_studio_ui", "reload_patched_build"]:
        if method in methods:
            print(f"[PASS] method present: {method}")
        else:
            print(f"[FAIL] method missing: {method}")
            failures.append(method)
    markers = [
        "Studio.Toolbar.TButton",
        "Athena Studio Compact Tile UI + Toolbar",
        "▶ Launch",
        "🔄 Reload",
        "🌐 Open Scout",
    ]
    for marker in markers:
        safe_marker = _safe_label(marker)
        if marker in text:
            print(f"[PASS] marker present: {safe_marker}")
        else:
            print(f"[FAIL] marker missing: {safe_marker}")
            failures.append(marker)
    if failures:
        print("\nOverall status: FAIL")
        return 1
    print("\nOverall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
