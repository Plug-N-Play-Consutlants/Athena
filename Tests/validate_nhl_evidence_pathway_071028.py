"""Offline regression for evidence consumption and season boundaries."""
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Reasoning.public_player_questions import classify_player_question
from Athena.public_team_performance import assess_team_performance
assert classify_player_question("How has William Nylander performed this season?") == "current_evidence"
assert classify_player_question("William Nylander profile") == "profile"
with patch("Providers.NHL.nhl_client.NHLClient.get_club_stats", return_value={"skaters": [{"firstName": {"default":"William"},"lastName":{"default":"Nylander"},"gamesPlayed":3,"points":5,"goals":2,"assists":3}], "goalies": []}):
    result = assess_team_performance("How are the Leafs performing this season?", "TOR", "Toronto Maple Leafs")
    assert "Nylander" in result["conclusion"] and "5 points" in result["conclusion"]
    assert "verified_team_standings_and_game_trends" in result["evidence"]["missing"]
with patch("Providers.NHL.nhl_client.NHLClient.get_club_stats", side_effect=TimeoutError()):
    result = assess_team_performance("How are the Leafs performing this season?", "TOR", "Toronto Maple Leafs")
    assert result["confidence"] < 0.5 and "verified_current_season_club_stats" in result["evidence"]["missing"]
print("NHL evidence pathway regression PASS")
