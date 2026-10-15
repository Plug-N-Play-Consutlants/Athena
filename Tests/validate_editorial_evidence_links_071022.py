"""Trade/standings are joined without unsupported causal claims."""
from Athena.Investigation.league_recap import compose_period_report
comparison={'status':'compared','teams':[
 {'team_id':'a','name':'Acquirer','rank':1,'rank_change':1,'period_points':38},
 {'team_id':'b','name':'Seller','rank':9,'rank_change':-2,'period_points':17},
 {'team_id':'c','name':'Leader','rank':3,'rank_change':3,'period_points':41},
 {'team_id':'d','name':'Other','rank':5,'rank_change':0,'period_points':22},
]}
editorial={'trades':[{'participants':['Acquirer','Seller'], 'received':{'Acquirer':['Player A'],'Seller':['Player B']}, 'lead':'Trade: Acquirer received Player A; Seller received Player B.'}], 'other_moves':[]}
report=compose_period_report(league_name='League',period=2,comparison=comparison,editorial=editorial,activity={})
assert 'Acquirer acquired Player A' in report
assert '38-point week' in report
assert 'contribution to that result is not established' in report
assert 'fell 2 places' in report or 'down 2 places' in report
print('PASS: joined trade and scoring context with causal restraint')
