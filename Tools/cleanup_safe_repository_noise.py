"""Safe repository-noise cleanup for AthenaEngine.

Default behavior deletes only reproducible Python bytecode/cache artifacts.
It does not move manifests, reports, raw data, archives, tests, or source modules.

Use --archive-root-history to move root-level CHANGE_MANIFEST_* and legacy README_*
files into Archive/Manifests/. This is intentionally opt-in.
"""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def delete_python_caches(root: Path, dry_run: bool) -> list[str]:
    actions: list[str] = []

    for cache_dir in sorted(root.rglob("__pycache__")):
        actions.append(f"delete_dir:{cache_dir.relative_to(root)}")
        if not dry_run:
            shutil.rmtree(cache_dir, ignore_errors=True)

    for pyc in sorted(root.rglob("*.pyc")):
        actions.append(f"delete_file:{pyc.relative_to(root)}")
        if not dry_run and pyc.exists():
            pyc.unlink()

    return actions


def archive_root_history(root: Path, dry_run: bool) -> list[str]:
    actions: list[str] = []
    destination = root / "Archive" / "Manifests"
    candidates = []

    candidates.extend(root.glob("CHANGE_MANIFEST_*.md"))
    candidates.extend(path for path in root.glob("README_*") if path.is_file())

    if candidates and not dry_run:
        destination.mkdir(parents=True, exist_ok=True)

    for source in sorted(candidates):
        target = destination / source.name
        actions.append(f"move:{source.relative_to(root)}->{target.relative_to(root)}")
        if not dry_run:
            if target.exists():
                target = destination / f"{source.stem}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}{source.suffix}"
            source.replace(target)

    return actions


def write_report(root: Path, actions: list[str], dry_run: bool) -> Path:
    report_dir = root / "Reports" / "cleanup"
    report_dir.mkdir(parents=True, exist_ok=True)
    report = report_dir / f"safe_repository_noise_cleanup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.txt"
    lines = [
        "AthenaEngine Safe Repository Noise Cleanup",
        "=" * 60,
        f"Dry run: {dry_run}",
        f"Action count: {len(actions)}",
        "",
        *actions,
        "",
    ]
    report.write_text("\n".join(lines), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Apply cleanup. Without this flag the script is dry-run only.")
    parser.add_argument(
        "--archive-root-history",
        action="store_true",
        help="Also move root-level historical manifests and legacy README_* files into Archive/Manifests/.",
    )
    args = parser.parse_args()

    root = repo_root()
    dry_run = not args.apply

    actions = delete_python_caches(root, dry_run=dry_run)
    if args.archive_root_history:
        actions.extend(archive_root_history(root, dry_run=dry_run))

    report = write_report(root, actions, dry_run=dry_run)

    print("Safe Repository Noise Cleanup")
    print("=" * 60)
    print(f"Root: {root}")
    print(f"Dry run: {dry_run}")
    print(f"Actions: {len(actions)}")
    print(f"Report: {report}")
    if dry_run:
        print("No files changed. Re-run with --apply to execute.")
    return 0


if __name__ == "__main__":
    main()
