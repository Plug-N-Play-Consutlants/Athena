"""Regression: synthesis shared between player analysis and organizational significance."""
from Athena.player_development import analyze_player_development
from Reasoning.Significance import assess_asset_significance, assess_organizational_significance
from Reasoning.Players.development_synthesis import synthesize_development

history=[{'season':20222023,'league':'NCAA','games_played':30,'points':16,'game_type':2},
         {'season':20232024,'league':'NCAA','games_played':31,'points':36,'game_type':2},
         {'season':20252026,'league':'NHL','games_played':4,'points':1,'game_type':2}]
asset={'name':'Sample Prospect','age':23,'development_history':history,'rights_state':{'control_status':'controlled'}}
assessment=analyze_player_development(asset,history=history)
assert 'Analytical synthesis:' in assessment['text']
assert '0.628' in assessment['text']
assert '4-game NHL sample' in assessment['text']
asset['asset_significance']=assess_asset_significance(asset)
org=assess_organizational_significance(asset,organization='Example Club')
assert '0.628' in org['summary'] and 'NCAA' in org['summary']
assert 'trade-value premium' in org['summary']
assert 'stable role' in org['summary']
assert not synthesize_development({})['state']=='established'
print('PASS: shared synthesis, observed performance, NHL attainment, organizational decision limits')
