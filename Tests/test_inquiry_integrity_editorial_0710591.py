"""Acceptance for 59.1: avoid accidental players, complete the named-team task."""
from __future__ import annotations

from Athena.fantasy_team_subject import named_team_roster_subject
from Athena.intent_resolution import select_executable_route
from Scout.conversation.context import ScoutContext
from Scout.conversation.router import route_question
from Knowledge.Intelligence.Entities.entity_extractor import resolve_entity
from Knowledge.Intelligence.Entities.fuzzy_match import similarity
from Knowledge.Intelligence.Routing.request_router import analyze_public_request
from Knowledge.Intelligence.Public.public_player_profiles import profile_for_entity
from Knowledge.Intelligence.Public.public_answers import player_profile_answer
from Scout.conversation.journalist_composition import compose_journalist_report

QUESTION = ("Where could Waterbury Wolverines improve its roster? Assess its actual scoring and "
            "positional weaknesses, player alternatives, fit and tradeoffs. Separate verified weaknesses from speculation.")


def fake_context():
    return ScoutContext(team_profiles=[
        {"team_name": "Waterbury Wolverines", "total_asset_value": 60.0},
        {"team_name": "Leeeroy Jenkins", "total_asset_value": 70.0}],
        player_master=[{"player_name": "R1", "owner_team": "Waterbury Wolverines", "position": "C"},
                       {"player_name": "R2", "owner_team": "Waterbury Wolverines", "position": "LW"},
                       {"player_name": "R3", "owner_team": "Leeeroy Jenkins", "position": "D"}])


def test_short_legacy_player_alias_does_not_match_incidental_word():
    assert similarity("improve", "ove") < .74
    assert similarity("machine", "mac") < .74
    assert similarity("novel", "ove") < .74
    assert resolve_entity(QUESTION, "player").entity is None
    assert analyze_public_request(QUESTION).route != "player_intelligence"
    for alias in ("Ove", "Ovi", "Ovechkin", "Alex Ovechkin"):
        match = resolve_entity(alias, "player")
        assert match.entity and match.entity.canonical_name == "Alex Ovechkin"
    assert resolve_entity("Tell me about Alex Ovechkin", "player").entity.canonical_name == "Alex Ovechkin"
    assert resolve_entity("Evaluate Auston Matthews this season", "player").entity.canonical_name == "Auston Matthews"


def test_named_team_requires_whole_phrase_and_explicit_assignment():
    ctx = fake_context()
    assert named_team_roster_subject(QUESTION, ctx) == "Waterbury Wolverines"
    assert named_team_roster_subject("How could Waterbury Wolverines improve its roster?", ctx) == "Waterbury Wolverines"
    assert named_team_roster_subject("How could Waterbury improve its roster?", ctx) is None
    assert named_team_roster_subject("Tell me about Waterbury Wolverines", ctx) is None
    assert named_team_roster_subject("Assess Waterbury Wolverines and Leeeroy Jenkins team rosters", ctx) is None
    assert named_team_roster_subject("Assess a fabricated Wolverines roster", ctx) is None


def test_public_and_fantasy_modes_both_preserve_named_team_assignment():
    ctx = fake_context()
    for mode in ("public", "fantasy"):
        route, reason = select_executable_route(QUESTION, mode, ctx)
        assert route == "fantasy_roster_diagnostic" and reason == "verified_named_fantasy_team_roster_assignment"
        answer = route_question(QUESTION, ctx=ctx, mode=mode)
        text = answer["public_comment"]
        assert answer["intent"] == "fantasy_roster_diagnostic"
        assert "Waterbury Wolverines" in text
        assert "C: 1" in text and "LW: 1" in text
        assert "no unrelated player's profile" in text.lower()
        assert "Alex Ovechkin" not in text
        assert "Leeeroy Jenkins" not in text
        assert answer["developer"]["athena_request"]["execution_owner"] == "athena_registered_specialist"
        assert answer["developer"]["athena_request"]["mode"] == "fantasy"
        assert answer["developer"]["scout_role"]["role"] == "analyst"
        assert answer["confidence"] < .8


def test_ovechkin_profile_retains_historical_context_without_official_stats(monkeypatch):
    from Knowledge.Intelligence.Entities.entity_registry import find_by_id
    from Knowledge.Intelligence.Public import public_answers
    entity = find_by_id("nhl.player.alex_ovechkin")
    profile = profile_for_entity(entity)
    monkeypatch.setattr(public_answers, "_player_experience_seed", lambda _p: {})
    monkeypatch.setattr(public_answers, "_build_reasoned_player_brief", lambda *_a, **_k: (None, {}, None))
    answer = player_profile_answer(fake_context(), profile, "Alex Ovechkin")
    body = answer["public_comment"]
    assert "historically significant goal scorer" in body
    assert "WSH" in body
    assert "does not imply that the player lacks an NHL career" in body
    assert "Current roster affiliation" in body
    assert "No NHL career" not in body
    assert answer["player"]["team"] == ""
    assert answer["title"].endswith("historical profile")


def test_journalism_connects_headline_and_scoreboard_and_avoids_score_dump():
    data = {
        "schema": "athena.league_period_research.v2", "league_name": "League", "period": 3,
        "findings": [
            {"kind": "surge", "team": "Bubba's Bruisers", "period_points": 42, "rank_change": 2, "rank": 3},
            {"kind": "scoring_leader", "team": "Leeeroy Jenkins", "period_points": 47},
            {"kind": "scoring_leader", "team": "Waterbury Wolverines", "period_points": 38},
            {"kind": "slide", "team": "Protect Hronek", "period_points": 16, "rank_change": -2, "rank": 5},
            {"kind": "slide", "team": "Urban Achievers", "period_points": 30, "rank_change": -2, "rank": 10},
            {"kind": "trade", "trade_count": 1, "exchanges": [{"received": {
                "Protect Hronek": ["Darnell Nurse"], "Bubba's Bruisers": ["Jack Eichel"]}}]},
            {"kind": "quiet_watch", "teams": ["Waterbury Wolverines", "Urban Achievers"], "observed_weeks": [2, 3]},
        ], "comparison": {"status": "compared", "period": 3, "baseline_period": 2,
                          "teams": [{"name": "Urban Achievers", "rank_change": -2}]},
        "storyline_continuity": {"status": "verified", "source": "canonical_period_standings",
                                  "signals": [{"team_name": "Bubba's Bruisers", "direction": "climb", "periods": [1,2,3], "overall_rank_change": 7},
                                              {"team_name": "Urban Achievers", "direction": "slide", "periods": [1,2,3], "overall_rank_change": -5}]},
        "coverage": {"period_standings": "available"}}
    report = compose_journalist_report(research=data)
    assert "Leeeroy Jenkins scored more this week (47)" in report
    assert "the rise of Bubba's Bruisers" in report  # no fabricated top scorer claim
    assert report.count("The league recorded 1 confirmed trade") == 1
    assert "trade" in report and "Jack Eichel" in report
    assert "The developing picture" in report and "two consecutive periods" in report
    assert report.count("The sequence is verified") == 0
    assert report.count("Those are verified arcs") == 1
    assert report.count("Those changes are standings facts") == 1
    assert "manager's reasoning" in report
    assert "cause" not in report[:report.index("The transaction wire")]
