"""Validate Athena Studio browser session and self-refresh controls."""
from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT / "Tools" / "athena_studio.py"
VERSION = ROOT / "Core" / "version.py"

def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")

def main() -> int:
    print("Athena Studio Browser/Self Refresh Validation")
    print("=" * 56)
    failures = 0
    studio = _text(STUDIO)
    checks = [
        ("Studio file exists", STUDIO.exists()),
        ("recognized version metadata", ("0.5.0-drop4e" in _text(VERSION) or __import__("re").search(r"ATHENA_VERSION\s*=\s*'\d+\.\d+\.\d+\.\d+\.\d+'|ATHENA_VERSION\s*=\s*\"\d+\.\d+\.\d+\.\d+\.\d+\"", _text(VERSION))) and "SCOUT_VERSION" in _text(VERSION)),
        ("Refresh Studio button", "Refresh Studio" in studio),
        ("Restart Studio button", "Restart Studio" in studio),
        ("open browser reload setting", "open_browser_after_reload" in studio),
        ("browser skipped message", "Browser open skipped" in studio),
        ("launch supports open_browser flag", "open_browser: bool | None" in studio),
        ("reload passes browser setting", "browser_open={should_open}" in studio),
        ("reload duplicate guard", "Reload Patched Build is already running" in studio),
    ]
    for label, ok in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")
        failures += 0 if ok else 1
    try:
        py_compile.compile(str(STUDIO), doraise=True)
        print("[PASS] Studio py_compile")
    except Exception as exc:
        print(f"[FAIL] Studio py_compile: {exc}")
        failures += 1
    print("\nOverall status:", "PASS" if failures == 0 else "FAIL")
    return 0 if failures == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
