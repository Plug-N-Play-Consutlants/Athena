"""Repository noise cleanup planner for AthenaEngine.

Default behavior is a dry run. This script identifies low-risk cleanup targets
but does not move or delete files unless --apply is passed.

Current low-risk targets:
- __pycache__ directories and *.pyc files.
- Root-level historical CHANGE_MANIFEST files can be moved to Archive/release_history_root
  only when --apply-manifests is also passed.

Runtime artifacts under Raw, Output, Reports, and Logs are reported but not
deleted by this script because they may be useful during acceptance testing.
"""
from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _rel(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")


def plan_cleanup() -> Dict[str, List[str]]:
    pycache = []
    pyc = []
    root_manifests = []
    root_readmes = []
    runtime_artifacts = []
    for path in PROJECT_ROOT.rglob("*"):
        if "__pycache__" in path.parts:
            pycache.append(_rel(path))
        elif path.is_file() and path.suffix == ".pyc":
            pyc.append(_rel(path))
        elif path.is_file() and path.parent == PROJECT_ROOT and path.name.startswith("CHANGE_MANIFEST"):
            root_manifests.append(_rel(path))
        elif path.is_file() and path.parent == PROJECT_ROOT and path.name.startswith("README_"):
            root_readmes.append(_rel(path))
        elif len(path.relative_to(PROJECT_ROOT).parts) > 0 and path.relative_to(PROJECT_ROOT).parts[0] in {"Raw", "Output", "Reports", "Logs"} and path.is_file():
            runtime_artifacts.append(_rel(path))
    return {
        "pycache_paths": sorted(set(pycache)),
        "pyc_files": sorted(set(pyc)),
        "root_change_manifests": sorted(root_manifests),
        "root_legacy_readmes": sorted(root_readmes),
        "runtime_artifacts_report_only": sorted(runtime_artifacts),
    }


def apply_cleanup(plan: Dict[str, List[str]], apply_manifests: bool = False) -> None:
    for rel in plan["pycache_paths"]:
        path = PROJECT_ROOT / rel
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
    for rel in plan["pyc_files"]:
        path = PROJECT_ROOT / rel
        if path.is_file():
            path.unlink(missing_ok=True)
    if apply_manifests:
        archive = PROJECT_ROOT / "Archive" / "release_history_root"
        archive.mkdir(parents=True, exist_ok=True)
        for rel in plan["root_change_manifests"] + plan["root_legacy_readmes"]:
            src = PROJECT_ROOT / rel
            if src.is_file():
                dst = archive / src.name
                if dst.exists():
                    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                    dst = archive / f"{src.stem}_{stamp}{src.suffix}"
                shutil.move(str(src), str(dst))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Delete Python cache files/directories.")
    parser.add_argument("--apply-manifests", action="store_true", help="Also move root manifests/readmes into Archive/release_history_root.")
    args = parser.parse_args()

    plan = plan_cleanup()
    print("AthenaEngine Repository Noise Cleanup Plan")
    print("=" * 52)
    for key, values in plan.items():
        print(f"{key}: {len(values)}")
        for item in values[:25]:
            print(f"  - {item}")
        if len(values) > 25:
            print(f"  ... {len(values) - 25} more")
    if not args.apply:
        print("\nDry run only. Re-run with --apply to remove Python cache files.")
        print("Use --apply --apply-manifests only after the release-history move is approved.")
        return 0

    apply_cleanup(plan, apply_manifests=args.apply_manifests)
    print("\nCleanup applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
