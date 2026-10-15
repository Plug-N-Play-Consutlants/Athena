from Reasoning.Players import build_player_intelligence
from Reasoning.Players.development_interpretation import interpret_development, summarize_development
from Reasoning.Significance import assess_asset_significance, assess_organizational_significance
from Athena.player_development import analyze_player_development

def run():
    rows=[{"season":20232024,"league":"NCAA","games_played":32,"points":30,"game_type":2},
          {"season":20242025,"league":"AHL","games_played":49,"points":26,"game_type":2},
          {"season":20252026,"league":"NHL","games_played":3,"points":1,"game_type":2},
          {"season":20252026,"league":"NHL","games_played":2,"points":2,"game_type":3}]
    player={"name":"Test Prospect","age":23,"relationship":"current_roster","development_history":rows}
    interpreted=interpret_development(rows)
    assert len(interpreted['timeline'])==3
    assert interpreted['latest_nhl_regular_season']['games']==3
    assert interpreted['nhl_sample_state']=='immature'
    assert len(interpreted['transitions'])==2
    profile=build_player_intelligence(player)
    assert profile['development_pathway']['interpretation']['first_observed_nhl_season']==2025
    result=analyze_player_development(player,history=rows)
    assert '3 NHL games' in result['text']
    assert 'NCAA (32 GP, 30 P)' in result['text']
    assert 'not proof of a late or early' in result['text']
    player['asset_significance']=assess_asset_significance(player)
    org=assess_organizational_significance(player,organization='Test Club')
    assert 'NCAA' in org['summary'] and 'NHL' in org['summary']
    assert 'attainment evidence' in org['summary']
    assert not interpret_development([])['timeline']
    print('PASS: chronology, playoff exclusion, NHL sample, interpretation, organizational consumption, empty history')
if __name__=='__main__':run()
