"""Offline regressions for authoritative team evidence and routing precedence."""
from pathlib import Path
import sys
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Athena.public_team_performance import assess_team_performance
from Scout.conversation.router import _is_team_performance_inquiry, _is_targeted_team_query
stats = {"skaters": [{"firstName": {"default": "William"}, "lastName": {"default": "Nylander"}, "gamesPlayed": 7, "points": 12}], "goalies": []}
standings = {"standings": [{"teamAbbrev": {"default": "TOR"}, "gamesPlayed": 7, "wins": 4, "losses": 2, "otLosses": 1, "points": 9, "goalFor": 24, "goalAgainst": 19}]}
schedule = {"games": [{"gameState": "OFF", "gameDate": "2026-10-10", "homeTeam": {"abbrev": "TOR", "score": 3}, "awayTeam": {"abbrev": "MTL", "score": 2}}]}
with patch('Providers.NHL.nhl_client.NHLClient.get_club_stats', return_value=stats), patch('Providers.NHL.nhl_client.NHLClient.get_team_standings_now', return_value=standings), patch('Providers.NHL.nhl_client.NHLClient.get_team_schedule_now', return_value=schedule):
    r = assess_team_performance('How are the Leafs doing this season?', 'TOR', 'Toronto Maple Leafs')
    assert '4-2-1' in r['conclusion'] and '1 verified completed games' in r['conclusion']
    assert 'verified_current_team_standings' not in r['evidence']['missing']
with patch('Providers.NHL.nhl_client.NHLClient.get_club_stats', return_value=stats), patch('Providers.NHL.nhl_client.NHLClient.get_team_standings_now', side_effect=TimeoutError()), patch('Providers.NHL.nhl_client.NHLClient.get_team_schedule_now', side_effect=TimeoutError()):
    r = assess_team_performance('How are the Leafs doing this season?', 'TOR', 'Toronto Maple Leafs')
    assert '12 points in 7 games' in r['conclusion']
    assert 'verified_current_team_standings' in r['evidence']['missing']
assert _is_targeted_team_query('What are the Leafs biggest roster needs?')
assert _is_team_performance_inquiry('What are the Leafs biggest roster needs?')
assert _is_team_performance_inquiry('How could Toronto improve its roster within cap constraints?')
print('Team composition evidence and routing semantics PASS')
