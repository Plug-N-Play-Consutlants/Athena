"""Hermetic integration check for team performance, roster and economic boundaries."""
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Athena.public_team_performance import assess_team_performance
from types import SimpleNamespace
stats = {"skaters": [{"firstName":{"default":"William"},"lastName":{"default":"Nylander"},"gamesPlayed":7,"points":12}],"goalies": []}
roster = {"forwards": [{}]*12, "defensemen": [{}]*6, "goalies": [{}]*2}
state = SimpleNamespace(aggregate_permitted=False, covered_contracts=lambda: [object()])
context = SimpleNamespace(league_year="2026-27",upper_limit=104000000)
with patch('Providers.NHL.nhl_client.NHLClient.get_club_stats', return_value=stats), \
     patch('Providers.NHL.nhl_client.NHLClient.get_current_roster', return_value=roster), \
     patch('Knowledge.Teams.team_economic_state.resolve_team_economic_state', return_value=state), \
     patch('Knowledge.Economics.league_season_context.resolve_league_season_context', return_value=context):
    result=assess_team_performance('What are the Leafs roster needs and cap options this season?', 'TOR','Toronto Maple Leafs')
    assert '12 points in 7 games' in result['conclusion']
    assert '12 forwards' in result['conclusion']
    assert '$104,000,000' in result['conclusion']
    assert 'cannot be calculated reliably' in result['conclusion']
    assert 'complete_verified_team_cap_ledger' in result['evidence']['missing']
with patch('Providers.NHL.nhl_client.NHLClient.get_club_stats', return_value=stats), \
     patch('Providers.NHL.nhl_client.NHLClient.get_current_roster', side_effect=TimeoutError()), \
     patch('Knowledge.Teams.team_economic_state.resolve_team_economic_state', side_effect=LookupError()):
    result=assess_team_performance('Leafs roster needs this season?', 'TOR','Toronto Maple Leafs')
    assert 'verified_current_roster' in result['evidence']['missing']
    assert 'canonical_team_economic_context' in result['evidence']['missing']
    assert '12 points in 7 games' in result['conclusion']
print('Team roster and economics bounded composition PASS')
