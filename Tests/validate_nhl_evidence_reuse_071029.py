"""Offline regression for exact-name club production fallback and movers."""
from unittest.mock import patch
from Athena.public_team_performance import official_team_player_row

class Client:
    def get_club_stats(self, team, season):
        assert team == 'TOR'
        return {'skaters': [{'firstName': {'default':'William'},'lastName':{'default':'Nylander'},'gamesPlayed':7,'points':12,'goals':4,'assists':8}]}

def run():
    with patch('Providers.NHL.nhl_client.NHLClient', return_value=Client()), patch('Knowledge.Intelligence.Public.player_evidence._target_season_id', return_value='20262027'):
        row = official_team_player_row('William Nylander', 'Toronto Maple Leafs')
        assert row['points'] == 12 and row['gp'] == 7
        assert official_team_player_row('William Nylander Jr', 'Toronto Maple Leafs') is None
    print('PASS: official NHL club-season identity-matched evidence reuse')

if __name__ == '__main__': run()
