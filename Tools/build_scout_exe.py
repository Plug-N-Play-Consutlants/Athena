"""Build a local Windows executable launcher for Athena Scout.

Usage from the Athena root:
    python Tools/build_scout_exe.py

This script requires PyInstaller. If it is not installed, run:
    python -m pip install pyinstaller

The output launcher will be created under dist/Athena Scout/Athena Scout.exe.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENTRY = PROJECT_ROOT / "launch.py"
DIST = PROJECT_ROOT / "dist"
BUILD = PROJECT_ROOT / "build" / "pyinstaller_scout"


def main() -> int:
    if not ENTRY.exists():
        print(f"ERROR: launch.py not found at {ENTRY}")
        return 1
    pyinstaller = shutil.which("pyinstaller")
    if not pyinstaller:
        print("PyInstaller is not installed.")
        print("Install it with: python -m pip install pyinstaller")
        return 1
    cmd = [
        pyinstaller,
        "--noconfirm",
        "--onedir",
        "--console",
        "--name",
        "Athena Scout",
        "--distpath",
        str(DIST),
        "--workpath",
        str(BUILD),
        str(ENTRY),
    ]
    print("Building Athena Scout launcher...")
    print(" ".join(cmd))
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), check=False)
    if result.returncode == 0:
        print("\nBuild complete:", DIST / "Athena Scout" / "Athena Scout.exe")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
