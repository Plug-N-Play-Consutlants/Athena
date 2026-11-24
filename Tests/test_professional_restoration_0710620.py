"""Professional profile evidence contract: authoritative latest-season vs current and identity boundaries."""
from __future__ import annotations

from Scout.conversation.router import route_question


def test_ovechkin_recent_dated_season_and_scouting_context(monkeypatch):
    monkeypatch.setenv("ATHENA_NHL_PLAYER_NETWORK", "0")
    for q in ("Alex Ovechkin", "Give me a complete scouting profile of Alex Ovechkin. Evaluate his current NHL performance, career achievements, historical scoring trends, playing style, strengths, weaknesses and age-related considerations."):
        a = route_question(q, mode="public")
        assert a["intent"] == "public_player_profile"
        assert "Latest verified NHL regular season (2025-26): 64 points in 82 games" in a["public_comment"]
        assert "one-timer" in a["public_comment"].lower()
        assert a["stats"] == {}, "Do not label last year's production as current"
        assert a["player"]["team"] == "WSH"
        assert a["developer"]["player_experience_seed"]["nhl_id"] == "8471214"


def test_marner_is_enriched_and_uses_verified_vegas_team(monkeypatch):
    monkeypatch.setenv("ATHENA_NHL_PLAYER_NETWORK", "0")
    for q in ("Mitch Marner", "Give me a scouting profile for Mitch Marner"):
        a = route_question(q, mode="public")
        assert a["intent"] == "public_player_profile"
        assert a["player"]["full_name"] == "Mitch Marner"
        assert a["player"]["team"] == "VGK"
        assert a["developer"]["player_experience_seed"]["nhl_id"] == "8478483"
        assert "Latest verified NHL regular season" in a["public_comment"]
        assert "playmaking" in a["public_comment"]
        assert "canonical public identity" not in a["title"].lower()


def test_aho_two_subjects_never_share_scoring_record(monkeypatch):
    monkeypatch.setenv("ATHENA_NHL_PLAYER_NETWORK", "0")
    a = route_question("Sebastian Aho", mode="public")
    assert a["intent"] == "public_entity_disambiguation"
    assert len(a["cards"]) == 2
    car = route_question("Sebastian Aho Carolina Hurricanes center", mode="public")
    swe = route_question("Sebastian Aho Swedish defenseman", mode="public")
    assert car["player"]["nationality"] == "Finland"
    assert swe["player"]["nationality"] == "Sweden"
    assert "80 points in 79 games" in car["public_comment"]
    assert "80 points in 79 games" not in swe["public_comment"]
    assert swe["stats"] == {}
    assert swe["developer"]["player_experience_seed"].get("nhl_id") is None


def test_legacy_editorial_week6_controls_remain_present():
    from Core.version import ATHENA_VERSION
    assert tuple(map(int, ATHENA_VERSION.split("."))) >= (0, 7, 10, 62, 0)
