"""Doctor for Athena runtime source-path cleanliness."""
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Tools.runtime_cleanup import PROJECT_ROOT, audit_runtime


def main() -> int:
    print("Runtime Cleanup Doctor")
    print("=" * 52)
    audit = audit_runtime()
    failures = 0

    checks = [
        ("canonical root", Path(audit["project_root"]).exists(), audit["project_root"]),
        ("Core/version.py", audit["core_version_exists"], str(PROJECT_ROOT / "Core" / "version.py")),
        ("Scout/app.py", audit["scout_app_exists"], str(PROJECT_ROOT / "Scout" / "app.py")),
        ("nested runtime duplicate", not audit["nested_runtime_duplicate_present"], str(PROJECT_ROOT / "Athena")),
        ("Athena engine package", audit["nested_athena_present"] and not audit["nested_runtime_duplicate_present"], str(PROJECT_ROOT / "Athena")),
    ]
    for label, ok, detail in checks:
        if ok:
            print(f"[PASS] {label}: {detail}")
        else:
            print(f"[WARN] {label}: {detail}")
            if label == "nested runtime duplicate":
                failures += 1

    print("\nNote: A top-level Athena/ engine package is expected. Only Athena/Core or Athena/Scout duplicates are failures.")
    print(f"\nOverall status: {'PASS' if failures == 0 else 'FAIL'}")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
