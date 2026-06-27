"""Doctor checks for Athena Studio tile-style command dashboard."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
STUDIO = ROOT / "Tools" / "athena_studio.py"

def main() -> int:
    print("Athena Studio Tile UI Doctor")
    print("=" * 60)
    failures: list[str] = []
    spec = importlib.util.spec_from_file_location("athena_studio_tile_probe", STUDIO)
    if spec is None or spec.loader is None:
        print("[FAIL] Could not load Studio module spec")
        return 1
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        print(f"[PASS] studio import: {STUDIO}")
    except Exception as exc:
        print(f"[FAIL] studio import: {exc}")
        return 1
    cls = getattr(module, "AthenaStudio", None)
    if cls is None:
        print("[FAIL] AthenaStudio class missing")
        return 1
    for name in ["_tile_text", "_tile_columns", "_button_group", "_setup_style", "_status_card"]:
        if hasattr(cls, name):
            print(f"[PASS] method present: {name}")
        else:
            print(f"[FAIL] method missing: {name}")
            failures.append(name)
    text = STUDIO.read_text(encoding="utf-8")
    for marker in ["Studio.Tile.TButton", "Athena Studio Compact Tile UI", "compact two-line dashboard tile label"]:
        if marker in text:
            print(f"[PASS] UI marker present: {marker}")
        else:
            print(f"[FAIL] UI marker missing: {marker}")
            failures.append(marker)
    if failures:
        print("\nOverall status: FAIL")
        return 1
    print("\nOverall status: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
