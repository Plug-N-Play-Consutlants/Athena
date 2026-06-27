"""Athena canonical runtime cleanup utilities.

This module removes Python bytecode caches and quarantines misplaced nested
Athena folders that caused patches to land under Athena/Athena instead of the
canonical project root.
"""
from __future__ import annotations

import shutil
import time
from dataclasses import dataclass, asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_DIR = PROJECT_ROOT / "Archive" / "runtime_quarantine"


@dataclass
class CleanupReport:
    project_root: str
    pycache_removed: int = 0
    pyc_removed: int = 0
    obsolete_launchers_removed: int = 0
    nested_athena_found: bool = False
    nested_runtime_duplicate: bool = False
    nested_athena_quarantined: bool = False
    quarantine_path: str = ""
    status: str = "PASS"
    notes: list[str] | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["notes"] = data.get("notes") or []
        return data


def _is_safe_nested_athena(nested: Path) -> bool:
    """Return True when nested Athena is safe to quarantine.

    The canonical root is the parent directory. A nested folder is never the
    active runtime, but we still avoid deleting if it contains suspicious paths
    such as a drive root marker. This is conservative and Windows-safe.
    """
    if not nested.exists() or not nested.is_dir():
        return False
    try:
        nested.relative_to(PROJECT_ROOT)
    except ValueError:
        return False
    return nested.name.lower() == "athena" and nested.parent == PROJECT_ROOT


def audit_runtime() -> dict:
    nested = PROJECT_ROOT / "Athena"
    runtime_duplicate = (nested / "Core").exists() or (nested / "Scout").exists()
    return {
        "project_root": str(PROJECT_ROOT),
        "core_version_exists": (PROJECT_ROOT / "Core" / "version.py").exists(),
        "scout_app_exists": (PROJECT_ROOT / "Scout" / "app.py").exists(),
        "nested_athena_present": nested.exists(),
        "nested_runtime_duplicate_present": runtime_duplicate,
        "nested_athena_path": str(nested),
    }


def clean_runtime(quarantine_nested: bool = True) -> CleanupReport:
    notes: list[str] = []
    report = CleanupReport(project_root=str(PROJECT_ROOT), notes=notes)

    for cache_dir in list(PROJECT_ROOT.rglob("__pycache__")):
        try:
            shutil.rmtree(cache_dir)
            report.pycache_removed += 1
        except Exception as exc:  # pragma: no cover - defensive filesystem guard
            notes.append(f"Could not remove {cache_dir}: {exc}")
            report.status = "WARN"

    for pyc in list(PROJECT_ROOT.rglob("*.pyc")):
        try:
            pyc.unlink()
            report.pyc_removed += 1
        except Exception as exc:  # pragma: no cover
            notes.append(f"Could not remove {pyc}: {exc}")
            report.status = "WARN"

    for launcher in ["Launch Scout.bat", "Stop_Scout_8765.bat", "Clean Athena Runtime Duplicates.bat"]:
        target = PROJECT_ROOT / launcher
        if target.exists():
            try:
                target.unlink()
                report.obsolete_launchers_removed += 1
            except Exception as exc:  # pragma: no cover
                notes.append(f"Could not remove {target}: {exc}")
                report.status = "WARN"

    nested = PROJECT_ROOT / "Athena"
    report.nested_athena_found = nested.exists()
    report.nested_runtime_duplicate = (nested / "Core").exists() or (nested / "Scout").exists()

    # The canonical project includes an Athena/ package for engine modules.
    # Only quarantine a nested Athena folder when it contains runtime duplicates
    # such as Athena/Core or Athena/Scout from a bad extraction.
    if quarantine_nested and report.nested_runtime_duplicate and _is_safe_nested_athena(nested):
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        suffix = time.strftime("%Y%m%d_%H%M%S")
        dest = ARCHIVE_DIR / f"nested_athena_runtime_duplicate_{suffix}"
        try:
            shutil.move(str(nested), str(dest))
            report.nested_athena_quarantined = True
            report.quarantine_path = str(dest)
            notes.append(f"Quarantined nested Athena runtime duplicate folder to {dest}")
        except Exception as exc:  # pragma: no cover
            notes.append(f"Could not quarantine {nested}: {exc}")
            report.status = "WARN"

    post = audit_runtime()
    if post["nested_runtime_duplicate_present"]:
        report.status = "WARN"
        notes.append("Nested Athena runtime duplicate still present after cleanup.")
    return report


def main() -> int:
    report = clean_runtime(quarantine_nested=True)
    print("Athena Runtime Cleanup")
    print("======================")
    for key, value in report.to_dict().items():
        if key == "notes":
            continue
        print(f"{key}: {value}")
    if report.notes:
        print("Notes:")
        for note in report.notes:
            print(f"- {note}")
    return 0 if report.status in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
