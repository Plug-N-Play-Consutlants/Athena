"""Validate Scout public analyst composition depth for v0.5.5.5.11."""
from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Knowledge.Intelligence.Routing.request_router import analyze_public_request
from Knowledge.Intelligence.Public.public_answers import player_profile_answer, team_profile_answer
from Knowledge.Intelligence.Public.public_player_profiles import get_public_player_profile
from Knowledge.Intelligence.Public.public_team_profiles import get_public_team_profile


FORBIDDEN = [
    "Athena is combining",
    "PIF Build",
    "Player Intelligence 4B.1",
    "evidence available",
    "Engine Conclusion",
    "Observed Facts",
    "Known Limitations",
]


def _answer(question: str) -> dict:
    ctx = SimpleNamespace(files_loaded=[])
    route = analyze_public_request(question)
    if route.route == "player_intelligence":
        profile = get_public_player_profile(route.entities[0].entity.entity_id)
        return player_profile_answer(ctx, profile, question)
    if route.route == "team_intelligence":
        profile = get_public_team_profile(route.entities[0].entity.entity_id)
        return team_profile_answer(ctx, profile, question)
    raise AssertionError(f"Unexpected route for {question!r}: {route.route}")


def _assert_clean(text: str) -> None:
    for token in FORBIDDEN:
        assert token.lower() not in text.lower(), f"Forbidden public diagnostic leaked: {token}"


def test_auston_matthews_is_analytical() -> None:
    answer = _answer("How good is Auston Matthews right now?")
    text = answer["natural_language_response"]
    _assert_clean(text)
    for token in ["2016 NHL Draft", "Rocket Richard", "captain", "deceptive release", "current statistical snapshot", "Current read", "Fantasy/value lens"]:
        assert token in text, f"Missing analytical player marker: {token}"


def test_dallas_stars_team_analysis_routes_and_composes() -> None:
    answer = _answer("How good are the Dallas Stars?")
    text = answer["natural_language_response"]
    _assert_clean(text)
    for token in ["Dallas Stars", "Core players", "Why they can be good", "What can hold them back", "Analytical read"]:
        assert token in text, f"Missing team analysis marker: {token}"


def test_edmonton_defense_is_synthesis_not_profile_dump() -> None:
    answer = _answer("Why have the Edmonton Oilers struggled defensively despite their offensive talent?")
    text = answer["natural_language_response"]
    _assert_clean(text)
    assert "roster-balance" in text
    assert "defensive-zone exits" in text
    assert "support layer" in text


if __name__ == "__main__":
    test_auston_matthews_is_analytical()
    test_dallas_stars_team_analysis_routes_and_composes()
    test_edmonton_defense_is_synthesis_not_profile_dump()
    print("Public analyst composition validation: PASS")
