"""Doctor for PIF-1 Build 004."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MODULES = [
    "Knowledge.Intelligence.Public.public_player_profiles",
    "Knowledge.Intelligence.Public.public_team_profiles",
    "Knowledge.Intelligence.Public.public_answers",
    "Knowledge.Intelligence.Entities.entity_registry",
    "Knowledge.Intelligence.Routing.request_router",
]


def main() -> int:
    print("PIF-1 Build 004 Doctor")
    print("=" * 64)
    failures: list[str] = []
    for mod in MODULES:
        try:
            module = importlib.import_module(mod)
            print(f"[PASS] import: {mod} -> {getattr(module, '__file__', 'built-in')}")
        except Exception as exc:
            print(f"[FAIL] import: {mod}: {exc}")
            failures.append(mod)
    try:
        from Knowledge.Intelligence.Public.public_team_profiles import public_team_profiles
        teams = public_team_profiles()
        if len(teams) >= 4:
            print(f"[PASS] public team profiles: {len(teams)} registered")
        else:
            print(f"[FAIL] public team profiles too small: {len(teams)}")
            failures.append("team_profiles")
    except Exception as exc:
        print(f"[FAIL] team profile inspection failed: {exc}")
        failures.append("team_profile_inspection")
    try:
        from Scout.conversation.router import route_question
        ans = route_question("Tell me about the Leafs", mode="public")
        if ans.get("intent") == "public_team_profile":
            print("[PASS] public team routing: Leafs -> public_team_profile")
        else:
            print(f"[FAIL] public team routing: expected public_team_profile, got {ans.get('intent')}")
            failures.append("team_routing")
    except Exception as exc:
        print(f"[FAIL] route inspection failed: {exc}")
        failures.append("route_inspection")
    if failures:
        print("\nOverall status: FAIL")
        return 1
    print("\nOverall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
