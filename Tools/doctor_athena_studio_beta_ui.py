"""Doctor checks for Athena Studio Beta UI."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
STUDIO = ROOT / "Tools" / "athena_studio.py"


def main() -> int:
    print("Athena Studio Beta UI Doctor")
    print("=" * 60)
    failures: list[str] = []
    if not STUDIO.exists():
        print("[FAIL] Studio file missing")
        return 1
    spec = importlib.util.spec_from_file_location("athena_studio_beta_probe", STUDIO)
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
    for name in ["_setup_style", "_status_card", "_tile_text", "_button_group", "refresh_studio_ui", "export_studio_log"]:
        if hasattr(cls, name):
            print(f"[PASS] method present: {name}")
        else:
            print(f"[FAIL] method missing: {name}")
            failures.append(name)
    if hasattr(module, "SimpleToolTip"):
        print("[PASS] SimpleToolTip available")
    else:
        print("[FAIL] SimpleToolTip missing")
        failures.append("SimpleToolTip")
    text = STUDIO.read_text(encoding="utf-8")
    for marker in ["Runtime Center", "Validation Center", "Doctor Center", "Logs & Diagnostics", "Athena Studio Beta Tile UI"]:
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
