"""Doctor for Athena v0.5.3.3.0 Multi-Sport Scout Routing & Studio UX."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CHECKS: list[tuple[str, bool, str]] = []

def check(name: str, condition: bool, detail: str = "") -> None:
    CHECKS.append((name, bool(condition), detail))


def main() -> int:
    router = importlib.import_module("Knowledge.Intelligence.Routing.multi_sport_router")
    route = router.route_multi_sport_query("Compare Auston Matthews vs Connor McDavid in the NHL")
    check("router_import", True, "multi_sport_router imported")
    check("sport_detected", route.sport == "hockey", f"sport={route.sport}")
    check("league_detected", route.league == "NHL", f"league={route.league}")
    check("source_metadata", "identity_registry" in route.allowed_sources, f"allowed={route.allowed_sources}")
    studio = (ROOT / "Tools" / "athena_studio.py").read_text(encoding="utf-8")
    check("studio_validate_everything_prominent", "✅ Validate Everything" in studio, "Validate Everything retained")
    check("studio_doctor_everything_prominent", "🩺 Doctor Everything" in studio, "Doctor Everything retained")
    check("legacy_validate_buttons_hidden", "✅ Validate Runtime" not in studio and "✅ Validate PIF" not in studio, "individual validator buttons hidden from UI")
    check("legacy_doctor_buttons_hidden", "🩺 Doctor Runtime" not in studio and "🩺 Doctor PIF" not in studio, "individual doctor buttons hidden from UI")
    failed = [row for row in CHECKS if not row[1]]
    print("Multi-Sport Scout Routing / Studio UX Doctor")
    print("=" * 56)
    for name, ok, detail in CHECKS:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"Overall status: {'PASS' if not failed else 'FAIL'}")
    return 1 if failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
