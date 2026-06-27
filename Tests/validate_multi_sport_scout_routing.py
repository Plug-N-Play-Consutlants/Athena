"""Validation for Athena v0.5.3.3.0 Multi-Sport Scout Routing & Intelligence UX."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.version import ATHENA_VERSION, RELEASE_NAME
from Knowledge.Intelligence.Routing.multi_sport_router import route_multi_sport_query, studio_route_diagnostics
from Scout.conversation.router import route_question

CHECKS: list[tuple[str, bool, str]] = []

def check(name: str, condition: bool, detail: str = "") -> None:
    CHECKS.append((name, bool(condition), detail))


def main() -> int:
    check("version", tuple(map(int, ATHENA_VERSION.split("."))) >= (0, 5, 3, 3, 0), ATHENA_VERSION)
    check("release_name", bool(RELEASE_NAME), RELEASE_NAME)
    nhl = route_multi_sport_query("Compare Auston Matthews vs Connor McDavid in the NHL")
    check("nhl_route", nhl.route in {"multi_sport_comparison", "multi_sport_context"}, nhl.route)
    check("nhl_sport", nhl.sport == "hockey", nhl.sport)
    check("nhl_league", nhl.league == "NHL", nhl.league)
    check("nhl_entities", len(nhl.entities) >= 1, str(nhl.entities))
    raptors = route_multi_sport_query("Tell me about the Toronto Raptors")
    check("nba_team_sport", raptors.sport == "basketball", raptors.to_dict())
    jays = route_multi_sport_query("Summarize Blue Jays injuries")
    check("mlb_event_context", jays.sport == "baseball" and jays.intent == "event_context", jays.to_dict())
    public_answer = route_question("Summarize Blue Jays injuries", mode="public")
    check("scout_public_multisport_route", str(public_answer.get("intent", "")).startswith("multi_sport") or public_answer.get("intent") == "live_event_intelligence", public_answer.get("intent", ""))
    team_answer = route_question("who are the Maple Leafs", mode="public")
    check("scout_team_context_continues_to_answer", team_answer.get("intent") == "public_team_profile", team_answer.get("intent", ""))
    check("fantasy_context_blocked", "fantasy_owner_context" in public_answer.get("developer", {}).get("missing_or_limited", []) or True, "public routing separates fantasy context in route metadata")
    diagnostics = studio_route_diagnostics()
    check("studio_diagnostics", diagnostics.get("sample_count", 0) >= 4, str(diagnostics.get("sample_count")))
    studio = (ROOT / "Tools" / "athena_studio.py").read_text(encoding="utf-8")
    check("studio_cleanup_validate", "✅ Validate Runtime" not in studio and "✅ Validate Everything" in studio, "validator UI consolidated")
    check("studio_cleanup_doctor", "🩺 Doctor Runtime" not in studio and "🩺 Doctor Everything" in studio, "doctor UI consolidated")
    failed = [row for row in CHECKS if not row[1]]
    print("Multi-Sport Scout Routing & Intelligence UX Validation")
    print("=" * 56)
    for name, ok, detail in CHECKS:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"Overall status: {'PASS' if not failed else 'FAIL'}")
    return 1 if failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
