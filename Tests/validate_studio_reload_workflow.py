"""Validate Athena Studio patched-build reload workflow."""
from __future__ import annotations

import ast
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT / "Tools" / "athena_studio.py"
RUN_SCOUT = ROOT / "Scout" / "run_scout.py"
VERSION = ROOT / "Core" / "version.py"


def _contains(path: Path, needle: str) -> bool:
    return needle in path.read_text(encoding="utf-8", errors="replace")


def _version() -> str:
    tree = ast.parse(VERSION.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "ATHENA_VERSION":
                    return str(node.value.value)
    return "unknown"


def main() -> int:
    print("Athena Studio Reload Workflow Validation")
    print("=" * 52)
    failures = 0
    checks = [
        ("studio exists", STUDIO.exists()),
        ("run_scout exists", RUN_SCOUT.exists()),
        ("version metadata available", _version().startswith("0.5.0-drop") or __import__("re").fullmatch(r"\d+\.\d+\.\d+\.\d+\.\d+", _version())),
        ("reload button label", _contains(STUDIO, "Reload Patched Build")),
        ("reload method", _contains(STUDIO, "def reload_patched_build")),
        ("sync stop helper", _contains(STUDIO, "def _stop_scout_sync")),
        ("cache purge helper", _contains(STUDIO, "def _purge_python_caches")),
        ("dynamic version refresh", _contains(STUDIO, "def _current_version_metadata")),
        ("strict port env", _contains(STUDIO, "SCOUT_STRICT_PORT")),
        ("strict port enforcement", _contains(RUN_SCOUT, "Strict Scout port mode requires port")),
    ]
    for label, ok in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")
        failures += 0 if ok else 1
    try:
        py_compile.compile(str(STUDIO), doraise=True)
        print("[PASS] studio py_compile")
    except Exception as exc:
        print(f"[FAIL] studio py_compile: {exc}")
        failures += 1
    try:
        py_compile.compile(str(RUN_SCOUT), doraise=True)
        print("[PASS] run_scout py_compile")
    except Exception as exc:
        print(f"[FAIL] run_scout py_compile: {exc}")
        failures += 1
    print("\nOverall status:", "PASS" if failures == 0 else "FAIL")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
