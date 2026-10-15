"""Regression: source-grounded significance, not a standings/trades inventory."""
from Athena.Investigation.league_recap import compose_period_report, investigate_period_stories

comparison = {"status":"compared", "teams":[
    {"team_id":"a","name":"Team A","rank":5,"rank_change":5,"period_points":41},
    {"team_id":"b","name":"Team B","rank":1,"rank_change":0,"period_points":38},
    {"team_id":"c","name":"Team C","rank":12,"rank_change":-5,"period_points":15},
]}
editorial = {"multiple_trade_teams":[("Team D",2)], "trades":[
    {"participants":["Team D","Team E"],"received":{"Team D":["Young One"],"Team E":["Veteran One"]},"lead":"Trade one"},
    {"participants":["Team D","Team F"],"received":{"Team D":["Young Two"],"Team F":["Veteran Two"]},"lead":"Trade two"}],
    "other_moves":[{"summary":"Team C added a prospect"}]}
activity={"transaction_count":3}
stories=investigate_period_stories(comparison, editorial, activity)
report=compose_period_report(league_name="Example League",period=2,comparison=comparison,editorial=editorial,activity=activity)
assert stories[0]["kind"] == "trade_cluster"
assert "Veteran One" in report and "Young Two" in report
assert "41 points" in report and "climbed 5 places" in report
assert "fell 5 places" in report
assert "Team C added a prospect" in report
assert "managerial intent" in report and "player contributions" in report
assert "The sharpest movements:" not in report
assert "Week 2" in report
missing=compose_period_report(league_name="Example League",period=3,comparison=None,editorial=None,activity={})
assert "insufficient" in missing and "41 points" not in missing
print("PASS: investigative league editorial significance and evidence boundaries")
