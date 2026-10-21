"""Regression: broad weekly editorial requests must not collapse to player leaders."""
from Athena.entry_policy import select_entry_route


def test_composite_report_wins_over_player_leaders():
    question = ("Give me a complete JHLPAA weekly report for the most recently completed scoring period: "
                "standings and movement, top 10 players by goals + assists, trades, transactions, "
                "waivers, and editorial analysis of the biggest stories.")
    for mode in ('fantasy', 'public'):
        decision = select_entry_route(question, mode)
        assert decision.route == 'league_recap', decision


def test_narrow_player_query_remains_specialized():
    assert select_entry_route('Who are the top 10 JHLPAA players by G+A for week 3?').route == 'league_player_period_leaders'


def test_narrow_calendar_query_remains_specialized():
    assert select_entry_route('When did the last completed JHLPAA scoring period end?').route == 'league_scoring_period_boundary'


def test_standings_only_retains_standings_route():
    assert select_entry_route('Show JHLPAA standings movement for week 3').route == 'league_period_standings'
