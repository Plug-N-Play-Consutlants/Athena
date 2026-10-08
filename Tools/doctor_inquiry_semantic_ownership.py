"""Verify that normalized Inquiry State owns transaction routing semantics."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "Tests" / "validate_inquiry_semantic_ownership.py"


def main() -> int:
    print("Inquiry Semantic Ownership Doctor")
    print("=" * 36)
    if not VALIDATOR.exists():
        print(f"[FAIL] validator exists: {VALIDATOR}")
        return 1
    result = subprocess.run([sys.executable, "-B", str(VALIDATOR)], cwd=str(ROOT), text=True, capture_output=True)
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip())
    print(f"Overall status: {'PASS' if result.returncode == 0 else 'FAIL'}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
