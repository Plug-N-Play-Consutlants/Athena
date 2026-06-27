"""Doctor for Athena Studio patched-build reload workflow."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    print("Athena Studio Reload Workflow Doctor")
    print("=" * 48)
    failures = 0
    required = [
        ROOT / "Tools" / "athena_studio.py",
        ROOT / "Scout" / "run_scout.py",
        ROOT / "Scout" / "stop_scout_windows.py",
        ROOT / "Core" / "version.py",
    ]
    for path in required:
        ok = path.exists()
        print(f"[{'PASS' if ok else 'FAIL'}] required file: {path}")
        failures += 0 if ok else 1
    spec = importlib.util.spec_from_file_location("athena_studio_doctor", ROOT / "Tools" / "athena_studio.py")
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls = getattr(module, "AthenaStudio", None)
        for method in ["reload_patched_build", "_reload_patched_build_sync", "_stop_scout_sync", "_wait_for_ports_clear", "_purge_python_caches"]:
            ok = cls is not None and hasattr(cls, method)
            print(f"[{'PASS' if ok else 'FAIL'}] Studio method: {method}")
            failures += 0 if ok else 1
    else:
        print("[FAIL] could not import Studio module")
        failures += 1
    print("\nOverall status:", "PASS" if failures == 0 else "FAIL")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
