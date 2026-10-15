"""Missing roster identity must be disclosed, not silently dropped or promoted to rights."""
from unittest.mock import patch
from Reasoning.Players.development_interpretation import interpret_development, summarize_development
from Scout.conversation.composition import _compose_organizational_assets_public
from Knowledge.Organizations import nhl_roster_evidence as evidence
from Athena import capability_handlers as handlers

def run():
    rows=[{"season":20222023,"league":"NCAA","games_played":30,"points":16,"game_type":2},
          {"season":20232024,"league":"NCAA","games_played":31,"points":36,"game_type":2}]
    i=interpret_development(rows)
    assert i['within_league_production_changes'][0]['change_ppg']>.6
    assert 'increased' in ' '.join(summarize_development(i))
    sample={"name":"Missing Prospect","nhl_player_id":"123","relationship":"historical_identity_only"}
    with patch.object(evidence,'acquire_historical_player_identities',return_value=[sample]) as historical,\
         patch.object(evidence,'acquire_team_player_evidence',return_value={"roster":[{"name":"Present Prospect","nhl_player_id":"456","relationship":"current_roster","team":"TOR","age":22}],"prospects":[],"acquisition_errors":[]}),\
         patch('Providers.NHL.nhl_client.NHLClient.get_player_landing',return_value={}):
        response=handlers._answer_nhl_organizational_assets(None,'Compare Present Prospect and Missing Prospect: which is more significant to Toronto and more reluctant to trade?')
    historical.assert_called_once_with('TOR',max_seasons=3)
    data=response['developer']['organizational_assets']
    assert [x['name'] for x in data['unverified_requested_players']]==['Missing Prospect']
    assert all(x['name']!='Missing Prospect' for x in data['reluctance_ranking'])
    rendered=_compose_organizational_assets_public(response,'')
    assert 'Missing Prospect' in rendered and 'current Toronto control has not been reverified' in rendered
    print('PASS: historical lookup, unresolved rights visibility, exclusion from ranking, within-league scoring interpretation')
if __name__=='__main__':run()
