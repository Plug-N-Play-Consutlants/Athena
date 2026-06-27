"""Validation for PIF-1 Build 003: public profile packs and Scout guardrails."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Knowledge.Intelligence.Public.public_player_profiles import public_player_profiles, public_profile_stats
from Knowledge.Intelligence.Routing.request_router import analyze_public_request
from Scout.conversation.router import route_question


def _assert(condition: bool, message: str, failures: list[str]) -> None:
    print(f"[{'PASS' if condition else 'FAIL'}] {message}")
    if not condition:
        failures.append(message)


def main() -> int:
    print("PIF-1 Build 003 Validation")
    print("=" * 64)
    failures: list[str] = []

    profiles = public_player_profiles()
    stats = public_profile_stats()
    _assert(len(profiles) >= 8, f"public player profiles seeded: {len(profiles)}", failures)
    _assert(stats.get("awards_seeded", 0) >= 8, f"award/legacy signals seeded: {stats.get('awards_seeded')}", failures)

    matthews = route_question("Austin Mathtwes", mode="public")
    _assert(matthews.get("intent") == "public_player_profile", "typo player prompt routes to public player profile", failures)
    _assert("fantasy" not in " ".join(matthews.get("developer", {}).get("knowledge_used", [])).lower(), "public typo answer does not use fantasy knowledge", failures)

    aho = route_question("Who is Sebastian Aho?", mode="public")
    _assert(aho.get("intent") == "public_entity_disambiguation", "Sebastian Aho asks for disambiguation", failures)
    _assert(len(aho.get("observed_facts") or []) >= 2, "Sebastian Aho returns at least two options", failures)

    comp = route_question("Compare Matthews and McDavid", mode="public")
    _assert(comp.get("intent") == "public_player_comparison", "public comparison uses public comparison answer", failures)
    _assert(any(str(card.get("label")).lower() == "fantasy" and str(card.get("value")).lower() == "skipped" for card in comp.get("cards", [])), "public comparison explicitly skips fantasy", failures)

    draft = route_question("If the NHL draft were today, who would go first?", mode="public")
    _assert(draft.get("intent") == "draft_intelligence_gap", "draft question routes to draft gap guardrail", failures)
    _assert("rulebook" in " ".join(draft.get("observed_facts", [])).lower(), "draft guardrail reports blocked rulebook domain", failures)

    pif = analyze_public_request("Compare Matthews and McDavid")
    _assert("fantasy_owner_data" in pif.blocked_domains, "PIF route blocks fantasy owner data for public comparison", failures)

    if failures:
        print("\nOverall status: FAIL")
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1
    print("\nOverall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
