"""Doctor checks for PIF-1 Build 003."""
from __future__ import annotations

import importlib
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CHECKS = [
    "Knowledge.Intelligence.Public.public_player_profiles",
    "Knowledge.Intelligence.Public.public_answers",
    "Knowledge.Intelligence.Routing.request_router",
    "Scout.conversation.router",
]


def main() -> int:
    print("PIF-1 Build 003 Doctor")
    print("=" * 64)
    failures: list[str] = []

    for rel in ["Scout/app.py", "Scout/conversation/router.py", "Tools/athena_studio.py"]:
        try:
            py_compile.compile(str(ROOT / rel), doraise=True)
            print(f"[PASS] py_compile: {rel}")
        except Exception as exc:
            print(f"[FAIL] py_compile: {rel}: {exc}")
            failures.append(rel)

    for module_name in CHECKS:
        try:
            module = importlib.import_module(module_name)
            print(f"[PASS] import: {module_name} -> {getattr(module, '__file__', 'unknown')}")
        except Exception as exc:
            print(f"[FAIL] import: {module_name}: {exc}")
            failures.append(module_name)

    try:
        from Knowledge.Intelligence.Public.public_player_profiles import public_player_profiles, public_profile_stats
        profiles = public_player_profiles()
        stats = public_profile_stats()
        print(f"[PASS] public profile pack: profiles={len(profiles)} awards={stats.get('awards_seeded')}")
        if len(profiles) < 8:
            failures.append("public_profile_count")
    except Exception as exc:
        print(f"[FAIL] public profile pack: {exc}")
        failures.append("public_profile_pack")

    try:
        from Scout.conversation.router import route_question
        probes = {
            "Austin Mathtwes": "public_player_profile",
            "Who is Sebastian Aho?": "public_entity_disambiguation",
            "Compare Matthews and McDavid": "public_player_comparison",
            "If the NHL draft were today, who would go first?": "draft_intelligence_gap",
        }
        for question, expected in probes.items():
            result = route_question(question, mode="public")
            actual = result.get("intent")
            if actual == expected:
                print(f"[PASS] public route: {question!r} -> {actual}")
            else:
                print(f"[FAIL] public route: {question!r} -> {actual}, expected {expected}")
                failures.append(question)
    except Exception as exc:
        print(f"[FAIL] public route probes: {exc}")
        failures.append("route_probes")

    if failures:
        print("\nOverall status: FAIL")
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1
    print("\nOverall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
