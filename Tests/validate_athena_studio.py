"""Validate Athena Studio alpha files."""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT / "Tools" / "athena_studio.py"
VERSION = ROOT / "Core" / "version.py"


def main() -> int:
    print("Athena Studio Validation")
    print("=" * 32)
    failures: list[str] = []
    for path in [STUDIO, VERSION]:
        if not path.exists():
            failures.append(f"missing: {path.relative_to(ROOT)}")
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"))
            print(f"[PASS] syntax: {path.relative_to(ROOT)}")
        except SyntaxError as exc:
            failures.append(f"syntax error in {path.relative_to(ROOT)}: {exc}")
    text = STUDIO.read_text(encoding="utf-8") if STUDIO.exists() else ""
    required = ["_read_version_metadata", "runtime_audit", "show_scout_log", "show_latest_debug", "restart_scout"]
    for needle in required:
        if needle in text:
            print(f"[PASS] studio contains {needle}")
        else:
            failures.append(f"studio missing {needle}")
    version_text = VERSION.read_text(encoding="utf-8") if VERSION.exists() else ""
    if "drop4e20" in version_text:
        print("[PASS] version advanced to drop4e20")
    else:
        failures.append("version did not advance to drop4e20")
    if failures:
        print("\nOverall status: FAIL")
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1
    print("\nOverall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
