"""Validation for PIF-1 Build 004: public team profiles and richer public comparison."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Knowledge.Intelligence.Public.public_player_profiles import public_player_profiles, public_profile_stats, profile_for_entity
from Knowledge.Intelligence.Public.public_team_profiles import public_team_profiles, public_team_profile_stats
from Knowledge.Intelligence.Entities.entity_registry import find_by_id
from Scout.conversation.router import route_question


def _assert(condition: bool, message: str, failures: list[str]) -> None:
    print(f"[{'PASS' if condition else 'FAIL'}] {message}")
    if not condition:
        failures.append(message)


def main() -> int:
    print("PIF-1 Build 004 Validation")
    print("=" * 64)
    failures: list[str] = []

    player_profiles = public_player_profiles()
    player_stats = public_profile_stats()
    team_profiles = public_team_profiles()
    team_stats = public_team_profile_stats()

    _assert(len(player_profiles) >= 9, f"public player profiles seeded: {len(player_profiles)}", failures)
    _assert(len(team_profiles) >= 4, f"public team profiles seeded: {len(team_profiles)}", failures)
    _assert(team_stats.get("questions_seeded", 0) >= 8, f"team question tags seeded: {team_stats.get('questions_seeded')}", failures)
    _assert("PIF Build 004" in " ".join(player_stats.get("guardrails", [])), "PIF Build 004 guardrail registered", failures)

    car_aho = profile_for_entity(find_by_id("nhl.player.sebastian_aho_car"))
    swe_aho = profile_for_entity(find_by_id("nhl.player.sebastian_aho_swe"))
    _assert(car_aho is not None and getattr(car_aho, "position", "") == "C", "Finnish/Carolina Sebastian Aho profile resolves", failures)
    _assert(swe_aho is not None and getattr(swe_aho, "position", "") == "D", "Swedish Sebastian Aho profile resolves", failures)

    leafs = route_question("Tell me about the Leafs", mode="public")
    _assert(leafs.get("intent") == "public_team_profile", "Leafs prompt routes to public team profile", failures)
    _assert("fantasy" not in " ".join(leafs.get("developer", {}).get("knowledge_used", [])).lower(), "public team answer does not use fantasy knowledge", failures)

    comp = route_question("Compare Matthews and McDavid", mode="public")
    text = " ".join(comp.get("observed_facts", []) or [])
    _assert(comp.get("intent") == "public_player_comparison", "public comparison uses comparison answer", failures)
    _assert("Career identity" in text and "Style" in text, "public comparison includes career identity and style sections", failures)
    _assert(any(str(card.get("label")).lower() == "fantasy" and str(card.get("value")).lower() == "skipped" for card in comp.get("cards", [])), "public comparison still skips fantasy by default", failures)

    if failures:
        print("\nOverall status: FAIL")
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1
    print("\nOverall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
