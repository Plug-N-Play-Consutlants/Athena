"""Offline D5 regression: verified synthesis, partial sources, acquisition timing."""
from unittest.mock import patch
from pathlib import Path
import sys

# Studio invokes this file directly; ensure the repository root is importable.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from Athena.public_team_performance import synthesize_verified_team_trends, assess_team_performance


def check(condition, name):
    assert condition, name
    print("[PASS]", name)


complete = {"standings": {"gamesPlayed": 10, "wins": 6, "losses": 3, "otLosses": 1,
    "last10Wins": 6, "last10Losses": 3, "last10OtLosses": 1,
    "streakCode": "W", "streakCount": 2, "goalFor": 30, "goalAgainst": 26}}
trend = synthesize_verified_team_trends(complete)
check(len(trend["statements"]) == 3 and "verified_streak" in trend["signals"], "verified_standings_synthesis")
check("+4" in " ".join(trend["statements"]), "goal_differential_calculation")
check(not synthesize_verified_team_trends({"missing": ["verified_current_team_standings"]})["statements"], "missing_standings_no_invention")
check(not synthesize_verified_team_trends({"standings": {"last10Wins": 7, "last10Losses": 3, "last10OtLosses": 5}})["statements"], "inconsistent_last_ten_rejected")

class Client:
    instances = 0
    def __init__(self): Client.instances += 1
    def get_club_stats(self, *args): return {"skaters": [], "goalies": []}
    def get_team_standings_now(self): return {"standings": [{"teamAbbrev": {"default": "TOR"}, **complete["standings"]}]}
    def get_team_schedule_now(self, *args): raise OSError("offline")
    def get_current_roster(self, *args): return {"forwards": [], "defensemen": [], "goalies": []}

with patch("Providers.NHL.nhl_client.NHLClient", Client), patch("Knowledge.Intelligence.Public.player_evidence._target_season_id", return_value="20262027"):
    result = assess_team_performance("Toronto Maple Leafs performance", "TOR", "Toronto Maple Leafs")
check(Client.instances == 1, "one_client_per_investigation")
check("Official last-ten form" in result["conclusion"], "trend_in_answer")
check("verified_recent_completed_games" in result["evidence"]["missing"], "failed_schedule_retained")
check(set(result["evidence"]["acquisition_timing_ms"]) == {"club_stats", "standings", "schedule", "roster_economics", "total"}, "bounded_stage_latency_observable")
print("Overall status: PASS")
