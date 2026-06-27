"""Validate Scout public composition depth and public-comment binding.

This acceptance validator targets the persistent Scout issue where route-specific
natural language was generated but not bound to the renderer-facing
``public_comment`` field. That caused Scout to show shallow fallback summaries
instead of the richer public answer.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Knowledge.Intelligence.Public.public_answers import player_profile_answer, team_profile_answer
from Knowledge.Intelligence.Public.public_player_profiles import get_public_player_profile
from Knowledge.Intelligence.Public.public_team_profiles import get_public_team_profile
from Scout.conversation.responses import response


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_response_helper_does_not_append_diagnostics() -> None:
    answer = response(
        intent="test",
        title="Test answer",
        engine_conclusion="This is the public conclusion.",
        observed_facts=["Fact A", "Fact B"],
        known_limitations=["Limitation A"],
        confidence=0.75,
    )
    public = answer.get("public_comment", "")
    _assert("Key evidence" not in public, "Fallback public response must not append observed facts.")
    _assert("Important limitation" not in public, "Fallback public response must not append limitations.")
    _assert(public == "This is the public conclusion.", "Fallback public response should be conclusion-only.")


def validate_team_public_comment_uses_composed_narrative() -> None:
    ctx = SimpleNamespace(files_loaded=[])
    profile = get_public_team_profile("nhl.team.toronto_maple_leafs")
    answer = team_profile_answer(ctx, profile, "Tell me about the Toronto Maple Leafs")
    public = answer.get("public_comment", "")
    natural = answer.get("natural_language_response", "")
    _assert(public == natural, "Team public_comment must be bound to the composed natural-language answer.")
    _assert("Key evidence:" not in public, "Team public answer must not show fallback evidence labels.")
    _assert("Important limitation:" not in public, "Team public answer must not show fallback limitation labels.")
    _assert("Analytical lens:" in public, "Team public answer should contain analytical framing.")
    _assert("Roster read:" in public, "Team public answer should contain roster-context framing.")
    _assert(len(public.split()) >= 90, "Team public answer is too shallow for acceptance mode.")


def validate_analytical_team_prompt_is_not_seed_dump() -> None:
    ctx = SimpleNamespace(files_loaded=[])
    profile = get_public_team_profile("nhl.team.edmonton_oilers")
    answer = team_profile_answer(ctx, profile, "Why have the Edmonton Oilers struggled defensively despite their offensive talent?")
    public = answer.get("public_comment", "")
    _assert(answer.get("public_comment") == answer.get("natural_language_response"), "Analytical public answer must bind to public_comment.")
    _assert("defensive problem is not explained by a lack of offensive talent" in public, "Oilers defensive prompt should receive an analytical response.")
    _assert("Key evidence:" not in public, "Analytical public answer must not show fallback evidence labels.")
    _assert(len(public.split()) >= 100, "Analytical team answer is too shallow.")


def validate_player_public_comment_binding() -> None:
    ctx = SimpleNamespace(files_loaded=[])
    profile = get_public_player_profile("nhl.player.auston_matthews")
    answer = player_profile_answer(ctx, profile, "How good is Auston Matthews right now?")
    public = answer.get("public_comment", "")
    _assert(public == answer.get("natural_language_response"), "Player public_comment must be bound to natural_language_response.")
    _assert("Athena is combining" not in public, "Player public answer must not expose legacy internal phrasing.")
    _assert("Key evidence:" not in public, "Player public answer must not show fallback evidence labels.")


def main() -> None:
    validate_response_helper_does_not_append_diagnostics()
    validate_team_public_comment_uses_composed_narrative()
    validate_analytical_team_prompt_is_not_seed_dump()
    validate_player_public_comment_binding()
    print("Scout composition depth fix validation: PASS")


if __name__ == "__main__":
    main()
