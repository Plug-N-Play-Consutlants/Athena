"""Validate Athena runtime cleanup tooling."""
from __future__ import annotations

import importlib
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    print("Runtime Cleanup Validation")
    print("=" * 52)
    failures = 0

    try:
        mod = importlib.import_module("Tools.runtime_cleanup")
        print(f"[PASS] import: Tools.runtime_cleanup -> {Path(mod.__file__).resolve()}")
    except Exception as exc:
        print(f"[FAIL] import: {exc}")
        return 1

    audit = mod.audit_runtime()
    if audit.get("core_version_exists"):
        print("[PASS] canonical Core/version.py exists")
    else:
        print("[FAIL] canonical Core/version.py missing")
        failures += 1

    if audit.get("scout_app_exists"):
        print("[PASS] canonical Scout/app.py exists")
    else:
        print("[FAIL] canonical Scout/app.py missing")
        failures += 1

    nested_path = Path(audit.get("nested_athena_path", PROJECT_ROOT / "Athena"))
    if nested_path == PROJECT_ROOT / "Athena":
        print(f"[PASS] nested audit path is scoped to canonical root: {nested_path}")
    else:
        print(f"[FAIL] nested audit path unexpected: {nested_path}")
        failures += 1

    status = "PASS" if failures == 0 else "FAIL"
    print(f"\nOverall status: {status}")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
