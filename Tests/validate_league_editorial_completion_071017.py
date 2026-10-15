"""Regression: explicit fantasy identity survives public mode; story retains evidence."""
from Athena.intent_resolution import select_executable_route
from Athena.Investigation.league_recap import compose_period_report
q = "Write an Around the JHLPAA Week 2 report using league standings and trades"
assert select_executable_route(q, "public") == ("", "explicit_fantasy_league_domain")
assert select_executable_route(q, "fantasy") == ("", "explicit_fantasy_league_domain")
comparison = {"status": "compared", "teams": [
    {"team_id": "a", "name": "Risers", "rank": 5, "rank_change": 5, "period_points": 41},
    {"team_id": "b", "name": "Climbers", "rank": 7, "rank_change": 6, "period_points": 25},
    {"team_id": "c", "name": "Fallers", "rank": 12, "rank_change": -5, "period_points": 15},
]}
editorial = {"multiple_trade_teams": [("Trader", 2)], "trades": [
    {"participants": ["Trader", "Other"], "received": {"Trader": ["Asset A"], "Other": ["Asset B"]}},
    {"participants": ["Trader", "Third"], "received": {"Trader": ["Asset C"], "Third": ["Asset D"]}},
], "other_moves": []}
report = compose_period_report(league_name="League", period=2, comparison=comparison, editorial=editorial, activity={})
for value in ("Asset A", "Asset B", "Asset C", "Asset D", "Risers", "Climbers", "Fallers"):
    assert value in report, value
assert "player contributions still need verification" in report
print("PASS: editorial domain boundary and evidence coverage")
