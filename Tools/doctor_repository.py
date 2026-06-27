"""Repository health doctor for AthenaEngine."""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ROOT_NAME = "AthenaEngine"
PYTHON_PACKAGE_NAME = "Athena"


def status(name: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'WARN' if name.startswith('warn') else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))
    return ok


def py_modules_under(base: Path) -> list[Path]:
    ignored = {"Archive", ".git", "__pycache__", "Logs", "Reports", "Output", "Raw"}
    modules: list[Path] = []
    for path in base.rglob("*.py"):
        if any(part in ignored for part in path.relative_to(base).parts):
            continue
        modules.append(path)
    return modules


def main() -> int:
    print("AthenaEngine Repository Doctor")
    print("=" * 64)
    failures = 0
    warnings = 0

    if not status("repository root is AthenaEngine", PROJECT_ROOT.name == EXPECTED_ROOT_NAME, str(PROJECT_ROOT)):
        failures += 1
    if not status("python package Athena exists", (PROJECT_ROOT / PYTHON_PACKAGE_NAME / "__init__.py").exists(), str(PROJECT_ROOT / PYTHON_PACKAGE_NAME)):
        failures += 1
    if not status("no Athena/Athena/Athena nesting", not (PROJECT_ROOT / PYTHON_PACKAGE_NAME / PYTHON_PACKAGE_NAME / PYTHON_PACKAGE_NAME).exists(), "historical broken nesting guard"):
        failures += 1

    version_file = PROJECT_ROOT / "Core" / "version.py"
    version_text = version_file.read_text(encoding="utf-8") if version_file.exists() else ""
    if not status("version metadata recognizes AthenaEngine", 'REPOSITORY_NAME = "AthenaEngine"' in version_text and 'PYTHON_PACKAGE_NAME = "Athena"' in version_text, str(version_file)):
        failures += 1

    launchers = [p.name for p in PROJECT_ROOT.glob("*.bat")] + [p.name for p in PROJECT_ROOT.glob("*.ps1")]
    duplicate_launcher_names = [name for name, count in Counter(launchers).items() if count > 1]
    if not status("no duplicate launcher filenames at root", not duplicate_launcher_names, ", ".join(duplicate_launcher_names)):
        failures += 1

    module_names = defaultdict(list)
    for path in py_modules_under(PROJECT_ROOT):
        module_names[path.name].append(path.relative_to(PROJECT_ROOT).as_posix())
    duplicate_candidates = {name: paths for name, paths in module_names.items() if len(paths) > 4 and name not in {"__init__.py"}}
    ok_duplicates = len(duplicate_candidates) == 0
    if not ok_duplicates:
        warnings += 1
        print(f"[WARN] warn duplicate module names: {duplicate_candidates}")
    else:
        print("[PASS] duplicate module name scan: no excessive duplicates")

    empty_dirs = []
    for path in PROJECT_ROOT.rglob("*"):
        if path.is_dir() and path.name not in {"__pycache__", ".git"}:
            try:
                if not any(path.iterdir()):
                    empty_dirs.append(path.relative_to(PROJECT_ROOT).as_posix())
            except Exception:
                pass
    if empty_dirs:
        warnings += 1
        print(f"[WARN] warn empty directories: {empty_dirs[:20]}")
    else:
        print("[PASS] empty directory scan")

    print(f"\nOverall status: {'PASS' if failures == 0 else 'FAIL'} | warnings={warnings}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
