"""Doctor checks for Athena Studio Phase 2."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
STUDIO = ROOT / "Tools" / "athena_studio.py"


def main() -> int:
    print("Athena Studio Phase 2 Doctor")
    print("=" * 60)
    failures: list[str] = []
    if not STUDIO.exists():
        print("[FAIL] Studio file missing")
        return 1
    spec = importlib.util.spec_from_file_location("athena_studio_probe", STUDIO)
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
    for name in ["show_pif_coverage", "show_knowledge_dashboard", "show_provider_dashboard"]:
        if hasattr(cls, name):
            print(f"[PASS] method present: {name}")
        else:
            print(f"[FAIL] method missing: {name}")
            failures.append(name)
    try:
        from Knowledge.Intelligence.Entities.identity_graph import graph_summary
        print(f"[PASS] identity graph available: {graph_summary().to_dict()}")
    except Exception as exc:
        print(f"[FAIL] identity graph unavailable: {exc}")
        failures.append("identity_graph")
    if failures:
        print("\nOverall status: FAIL")
        return 1
    print("\nOverall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
