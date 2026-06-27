"""Doctor for Athena Studio browser session and self-refresh controls."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT / "Tools" / "athena_studio.py"

def main() -> int:
    print("Athena Studio Browser/Self Refresh Doctor")
    print("=" * 52)
    failures = 0
    spec = importlib.util.spec_from_file_location("athena_studio_e31", STUDIO)
    if not spec or not spec.loader:
        print("[FAIL] could not load Studio spec")
        return 1
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cls = getattr(module, "AthenaStudio", None)
    for method in [
        "refresh_studio_ui",
        "restart_studio",
        "reload_patched_build",
        "_reload_patched_build_sync",
        "_toggle_open_browser_after_reload",
        "_load_studio_settings",
        "_save_studio_settings",
        "launch_scout",
        "open_scout",
    ]:
        ok = cls is not None and hasattr(cls, method)
        print(f"[{'PASS' if ok else 'FAIL'}] Studio method: {method}")
        failures += 0 if ok else 1
    print("\nOverall status:", "PASS" if failures == 0 else "FAIL")
    return 0 if failures == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
