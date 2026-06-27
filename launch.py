"""Athena Alpha launcher with visible runtime diagnostics."""
from __future__ import annotations

from pathlib import Path
import os
import shutil
import sys
import traceback

PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIR = PROJECT_ROOT / "Logs"
LOG_FILE = LOG_DIR / "scout_launch_error.txt"



def _purge_runtime_cache() -> None:
    """Remove Python bytecode caches that can make local alpha launches look stale."""
    for cache_dir in PROJECT_ROOT.rglob("__pycache__"):
        try:
            shutil.rmtree(cache_dir)
        except Exception:
            pass

def _write_error(exc: BaseException) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.write_text("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)), encoding="utf-8")


def main() -> int:
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    _purge_runtime_cache()
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    try:
        from Core.version import SCOUT_VERSION
        print(f"Launching canonical Scout runtime: {SCOUT_VERSION}")
        print(f"Project root: {PROJECT_ROOT}")
        print(f"Scout app: {PROJECT_ROOT / 'Scout' / 'app.py'}")
        from Scout.run_scout import launch_scout
        managed = os.environ.get("ATHENA_STUDIO_MANAGED") == "1"
        return int(launch_scout(open_browser=not managed) or 0)
    except KeyboardInterrupt:
        print("\nScout stopped by user.")
        return 0
    except Exception as exc:
        _write_error(exc)
        print("\nATHENA SCOUT FAILED TO START")
        print("=" * 60)
        print(str(exc))
        print(f"\nFull traceback written to: {LOG_FILE}")
        print("\nPaste that file back into the chat if this happens again.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
