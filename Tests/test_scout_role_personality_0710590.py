"""v59: role-aware presentation, evidence-guarded league journalism."""
from __future__ import annotations

from Scout.conversation.role_intelligence import (
    attach_role_metadata, compose_consultative_answer, select_scout_role,
)
from Scout.conversation.journalist_composition import compose_journalist_report
from Scout.conversation.league_recap_narrative import compose_period_report


def sample_research():
    return {"schema": "athena.league_period_research.v2", "league_name": "Sample Hockey League", "period": 3,
            "period_calendar": {"start": "2026-10-12", "end": "2026-10-18"},
            "comparison": {"status": "compared", "period": 3, "baseline_period": 2,
                           "teams": [{"team_id": "alpha", "name": "Alpha", "rank": 1, "rank_change": 2,
                                      "period_points": 48},
                                     {"team_id": "beta", "name": "Beta", "rank": 3, "rank_change": -2,
                                      "period_points": 20}]},
            "findings": [
                {"kind": "surge", "team": "Alpha", "rank": 1, "rank_change": 2,
                 "period_points": 48, "top_score": True, "significance": 102},
                {"kind": "scoring_leader", "team": "Gamma", "period_points": 40, "significance": 94},
                {"kind": "slide", "team": "Beta", "rank": 3, "rank_change": -2,
                 "period_points": 20, "significance": 72},
                {"kind": "trade", "trade_count": 1, "significance": 75,
                 "exchanges": [{"received": {"Alpha": ["Player A"], "Beta": ["Player B"]}}]},
                {"kind": "quiet_watch", "teams": ["Beta"], "observed_weeks": [2,3], "significance": 20},
            ], "nhl_player_leaders": [{"player_name": "Player Z", "points": 5, "goals": 3, "assists": 2, "games_played": 3}],
            "coverage": {"period_standings": "available", "player_period_production": "verified_nhl_window_only"}}


def test_roles_follow_assignment_not_ui_mode():
    expectations = {
        "What's happening around the JHLPAA this week?": "journalist",
        "Write this week's fun league recap including trades": "journalist",
        "Compare Connor McDavid and Auston Matthews": "analyst",
        "Which forward would improve my roster?": "analyst",
        "Should we trade this prospect or retain draft capital?": "executive",
        "How can Toronto improve its salary cap position?": "executive",
        "Reconcile JHLPAA scoring for Weeks 2 and 3; then write the editorial recap": "auditor",
        "Debug the fantasy player identity gaps": "auditor",
    }
    for question, role in expectations.items():
        assert select_scout_role(question, mode="fantasy").role == role, question
    assert select_scout_role("What's happening around the JHLPAA?", mode="public").role == "journalist"
    assert select_scout_role("Evaluate this forward as a scout", mode="fantasy").role == "analyst"


def test_role_metadata_does_not_modify_facts_or_confidence():
    answer = {"intent": "league_player_comparison", "confidence": .72, "observed_facts": ["confirmed"],
              "natural_language_response": "A measured comparison", "developer": {"key": "value"}}
    attach_role_metadata(answer, question="Compare two prospects")
    assert answer["developer"]["scout_role"]["role"] == "analyst"
    assert answer["confidence"] == .72 and answer["observed_facts"] == ["confirmed"]
    assert answer["developer"]["key"] == "value"


def test_journalist_uses_only_verifiable_story_evidence_and_differs_from_audit():
    research = sample_research()
    report = compose_journalist_report(research=research)
    audit = compose_period_report(research=research)
    assert "The headline" in report and "The developing picture" in report
    assert "The transaction wire" in report and "The quiet corner" in report
    assert "Alpha" in report and "48" in report and "Player A" in report
    assert "Beta" in report and "Player B" in report
    assert "NHL performances, not independently verified fantasy lineup credit" in report
    assert "Who’s keeping quiet" not in report
    assert report != audit
    assert report.count("The league recorded 1 confirmed trade") == 1
    assert not any(word in report.lower() for word in ("lazy manager", "manager gave up", "deliberately tanked", "confirmed feud"))


def test_empty_evidence_is_never_embellished_as_news():
    data = sample_research()
    data["findings"] = []
    result = compose_journalist_report(research=data)
    assert "isn't enough verified activity" in result
    assert "Player A" not in result and "48 points" not in result


def test_unverified_movements_do_not_become_streaks_or_motives():
    data = sample_research()
    data["comparison"] = {"status": "baseline_missing", "teams": []}
    result = compose_journalist_report(research=data)
    assert "The developing picture" not in result
    assert "between Weeks" not in result
    assert "trade is a fact" not in result.lower() or "pay off" in result.lower()


def test_executive_and_analyst_have_distinct_responsible_voices():
    for question, expected in [
        ("Compare these players for roster fit", "Scouting assessment"),
        ("Should we trade this prospect for a draft pick?", "Executive decision brief"),
    ]:
        result = {"intent": "league_player_comparison", "confidence": .8,
                  "engine_conclusion": "The observed production favors Player A.",
                  "natural_language_response": "The observed production favors Player A.",
                  "known_limitations": ["Current deployment is unverified."], "developer": {}}
        role = select_scout_role(question, intent=result["intent"])
        composed = compose_consultative_answer(result, question=question, role=role)
        assert composed["natural_language_response"].startswith(expected)
        assert "The observed production favors Player A." in composed["natural_language_response"]
        assert "Current deployment is unverified." in composed["natural_language_response"]
        assert composed["developer"]["scout_role_composition"] == "bounded_consultative_framing"
        assert composed["public_comment"] == composed["response_text"] == composed["natural_language_response"]
        assert composed["athena_response"]["schema"] if "schema" in composed["athena_response"] else composed["athena_response"]
    gap = {"intent": "public_intelligence_gap", "confidence": .2,
           "natural_language_response": "No verified cap evidence", "developer": {}}
    assert compose_consultative_answer(gap, question="Should we trade?", role=select_scout_role("Should we trade?"))["natural_language_response"] == "No verified cap evidence"


def test_audit_composition_retains_existing_numerical_diagnostics():
    data = sample_research()
    data["multi_period_scoring"] = {"requested_periods": [2], "periods": [{
        "period": 2, "status": "partial", "numeric_matched_teams": 1, "identity_complete_teams": 1,
        "team_count": 2, "reserve_nhl_points_excluded": 3,
        "teams": [{"team_name": "Beta", "difference": 1, "fantrax_points": 20,
                   "identified_active_nhl_points": 19, "unmatched_active_ids": ["f123"]}]}]}
    report = compose_period_report(research=data)
    assert "Week 2: 1/2" in report
    assert "Beta: 19 NHL ACTIVE vs 20 Fantrax (difference +1)" in report
    assert "unresolved ACTIVE IDs: f123" in report


def test_verified_multiweek_storyline_requires_complete_same_league_history(tmp_path):
    from Athena.Investigation.standings_archive import save_snapshot
    from Athena.Investigation.editorial_storylines import investigate_storyline_continuity
    for period, a_rank, b_rank in [(1, 3, 1), (2, 2, 2), (3, 1, 3)]:
        snapshot = {"league_id": "league1", "season": 2026, "period": period,
                    "source": "fixture", "timeframe": "FROM_SEASON_START", "complete": True,
                    "teams": [{"team_id": "a", "name": "Alpha", "rank": a_rank, "points": period * 15},
                              {"team_id": "b", "name": "Beta", "rank": b_rank, "points": period * 10},
                              {"team_id": "c", "name": "Gamma", "rank": 2 if period != 2 else 1,
                               "points": period * 8}]}
        # Avoid fabricated standings ranks: two teams may tie but other ranks must be valid.
        if period == 1:
            snapshot["teams"][2]["rank"] = 2
        elif period == 2:
            snapshot["teams"][2]["rank"] = 1
        else:
            snapshot["teams"][2]["rank"] = 2
        save_snapshot(tmp_path, snapshot)
    result = investigate_storyline_continuity(tmp_path, "league1", 2026, 3)
    assert result["status"] == "verified"
    assert next(r for r in result["signals"] if r["team_name"] == "Alpha")["direction"] == "climb"
    research = sample_research()
    research["storyline_continuity"] = result
    assert "two consecutive periods" in compose_journalist_report(research=research)
    assert investigate_storyline_continuity(tmp_path, "wrong_league", 2026, 3)["signals"] == []
    assert investigate_storyline_continuity(tmp_path, "league1", 2025, 3)["signals"] == []
    assert investigate_storyline_continuity(tmp_path, "league1", 2026, 4)["signals"] == []


def test_real_scout_public_channel_updates_all_advisory_aliases(monkeypatch):
    from Scout.conversation import router
    from Scout.conversation.responses import response
    stub = response(intent="league_player_comparison", title="Forward comparison",
                    engine_conclusion="Player A owns the stronger verified goal rate.",
                    known_limitations=["Current deployment is unknown."], confidence=.8)
    monkeypatch.setattr(router, "_route_question_without_role", lambda *args, **kwargs: dict(stub))
    rendered = router.route_question("Compare their scoring rates as an NHL scout", mode="fantasy")
    assert rendered["developer"]["scout_role"]["role"] == "analyst"
    assert rendered["public_comment"].startswith("Scouting assessment")
    assert rendered["response_text"] == rendered["public_comment"]
    assert rendered["scout_message"] == rendered["public_comment"]
    assert rendered["natural_language_response"] == rendered["public_comment"]
    assert rendered["engine_conclusion"] == "Player A owns the stronger verified goal rate."
    assert rendered.get("athena_response")
