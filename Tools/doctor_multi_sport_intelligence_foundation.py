"""Doctor for Athena v0.5.5.0.0 Multi-Sport Intelligence Foundation."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CHECKS: list[tuple[str, bool, str]] = []

def check(name: str, condition: bool, detail: str = "") -> None:
    CHECKS.append((name, bool(condition), detail))


def main() -> int:
    print("Multi-Sport Intelligence Foundation Doctor")
    print("=" * 64)
    required = [
        "Sports/__init__.py",
        "Sports/registry.py",
        "Intelligence/Foundation/__init__.py",
        "Intelligence/Foundation/modules.py",
        "Tests/validate_multi_sport_intelligence_foundation.py",
        "Tools/doctor_multi_sport_intelligence_foundation.py",
    ]
    for rel in required:
        check(f"required file exists: {rel}", (ROOT / rel).exists(), rel)

    from Core.version import ATHENA_VERSION, ATHENA_BUILD, RELEASE_NAME, VERSION_SCHEMA
    check("version metadata", ATHENA_VERSION == ATHENA_BUILD and ATHENA_VERSION >= "0.5.5.0.0" and VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", ATHENA_VERSION)
    check("release name", bool(RELEASE_NAME), RELEASE_NAME)

    from Sports import SPORT_REGISTRY_VERSION, seed_sport_registry, sport_registry_diagnostics
    sport_registry = seed_sport_registry()
    sport_stats = sport_registry.stats()
    check("sport registry version", SPORT_REGISTRY_VERSION == "0.5.5.0.0", SPORT_REGISTRY_VERSION)
    check("five core sports registered", {"hockey", "football", "baseball", "basketball", "soccer"}.issubset(set(sport_stats["sport_ids"])), str(sport_stats["sport_ids"]))
    check("core leagues registered", {"NHL", "NFL", "MLB", "NBA"}.issubset(set(sport_stats["leagues"])), str(sport_stats["leagues"]))
    check("sport diagnostics serializable", sport_registry_diagnostics()["panel"] == "sport_registry", str(sport_registry_diagnostics().keys()))

    from Intelligence.Foundation import (
        INTELLIGENCE_FOUNDATION_VERSION,
        capability_matrix,
        seed_intelligence_registry,
        select_intelligence_modules,
        studio_intelligence_diagnostics,
    )
    registry = seed_intelligence_registry()
    stats = registry.stats()
    check("intelligence version", INTELLIGENCE_FOUNDATION_VERSION == "0.5.5.0.0", INTELLIGENCE_FOUNDATION_VERSION)
    check("module registry includes ten modules", stats["modules"] >= 10, str(stats))
    check("provider-neutral modules", stats["provider_neutral"] is True, str(stats))
    check("player/team/event module families available", {"player_assessment", "team_assessment", "event_assessment"}.issubset(set(stats["module_ids"])), str(stats["module_ids"]))
    event_modules = select_intelligence_modules(intent="event_context", sport="baseball")
    check("event context selects event modules", event_modules and event_modules[0].module_id == "event_assessment", str([m.module_id for m in event_modules]))
    matrix = capability_matrix()
    check("capability matrix covers sports", matrix["status"] == "pass" and len(matrix["sports"]) >= 5, str(matrix.get("sports", [])[:2]))
    check("Studio intelligence diagnostics", studio_intelligence_diagnostics()["panel"] == "intelligence", str(studio_intelligence_diagnostics().keys()))

    from Knowledge.Intelligence.Routing.multi_sport_router import route_multi_sport_query, studio_route_diagnostics
    route = route_multi_sport_query("Summarize Blue Jays injuries")
    check("routing includes intelligence module selection", "event_assessment" in route.intelligence_modules, str(route.to_dict()))
    check("routing exposes capability sources", "event_intelligence" in route.capability_sources, str(route.capability_sources))
    diagnostics = studio_route_diagnostics()
    check("route diagnostics expose intelligence", diagnostics.get("intelligence", {}).get("panel") == "intelligence", str(diagnostics.keys()))

    failed = [row for row in CHECKS if not row[1]]
    for name, ok, detail in CHECKS:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"Overall status: {'PASS' if not failed else 'FAIL'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
