"""Validation for Athena v0.5.5.0.0 Multi-Sport Intelligence Foundation."""
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
    from Core.version import ATHENA_VERSION, RELEASE_NAME
    from Sports import seed_sport_registry
    from Intelligence.Foundation import (
        capability_matrix,
        seed_intelligence_registry,
        select_intelligence_modules,
        studio_intelligence_diagnostics,
    )
    from Knowledge.Intelligence.Routing.multi_sport_router import route_multi_sport_query, studio_route_diagnostics
    from Knowledge.Identity import resolve_identity
    from Knowledge.Events import canonical_event_payload, canonical_event_types, normalize_event_payload

    check("version", tuple(map(int, ATHENA_VERSION.split("."))) >= (0, 5, 5, 0, 0), ATHENA_VERSION)
    check("release", bool(RELEASE_NAME), RELEASE_NAME)

    sports = seed_sport_registry()
    stats = sports.stats()
    check("registered sports", stats["sports"] >= 5, str(stats))
    check("sport metadata includes taxonomies", "injury" in stats["event_types"] and stats["positions"] >= 20, str(stats))
    check("league to sport lookup", sports.for_league("NBA") is not None and sports.for_league("NBA").sport_id == "basketball", "NBA")

    intelligence = seed_intelligence_registry()
    istats = intelligence.stats()
    check("registered intelligence modules", istats["modules"] >= 10, str(istats))
    check("fantasy modules are present but modular", {"draft_assessment", "trade_assessment", "roster_assessment"}.issubset(set(istats["module_ids"])), str(istats["module_ids"]))
    check("sport-aware module filtering", len(intelligence.for_sport("soccer")) < len(intelligence.all_modules()) and len(intelligence.for_sport("hockey")) >= 10, "soccer vs hockey")
    selected = select_intelligence_modules(intent="comparison", sport="hockey", entity_type="player")
    check("comparison selects assessment modules", {"player_assessment", "historical_assessment"}.issubset({m.module_id for m in selected}), str([m.module_id for m in selected]))

    matrix = capability_matrix()
    check("capability discovery is self describing", matrix["status"] == "pass" and matrix["registry"]["modules"] >= 10, str(matrix["registry"]))
    studio = studio_intelligence_diagnostics()
    check("Studio diagnostics payload", studio["panel"] == "intelligence" and studio["registered_modules"] >= 10, str(studio.keys()))

    nhl = route_multi_sport_query("Compare Auston Matthews vs Connor McDavid in the NHL")
    mlb = route_multi_sport_query("Summarize Blue Jays injuries")
    nba = route_multi_sport_query("Tell me about the Toronto Raptors")
    check("nhl route has modules", nhl.sport == "hockey" and "player_assessment" in nhl.intelligence_modules, str(nhl.to_dict()))
    check("mlb event route has event module", mlb.sport == "baseball" and "event_assessment" in mlb.intelligence_modules, str(mlb.to_dict()))
    check("nba route capability sources", nba.sport == "basketball" and nba.capability_sources, str(nba.to_dict()))
    check("route diagnostics include intelligence matrix", studio_route_diagnostics()["intelligence"]["panel"] == "intelligence", str(studio_route_diagnostics().keys()))

    # Guardrails from prior validated baselines.
    aho = resolve_identity("Sebastian Aho")
    check("identity ambiguity preserved", aho.ambiguous is True, str(aho.to_dict()))
    check("Knowledge.Events compatibility preserved", callable(canonical_event_payload) and callable(normalize_event_payload) and callable(canonical_event_types), "events imports")

    studio_file = (ROOT / "Tools" / "athena_studio.py").read_text(encoding="utf-8")
    check("Studio exposes intelligence card", "Intelligence" in studio_file and "show_intelligence_dashboard" in studio_file, "Studio integration")
    check("button width opportunistic polish", "width=8" in studio_file or "width=9" in studio_file, "compact tile width")

    failed = [row for row in CHECKS if not row[1]]
    print("Multi-Sport Intelligence Foundation Validation")
    print("=" * 64)
    for name, ok, detail in CHECKS:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"Overall status: {'PASS' if not failed else 'FAIL'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
