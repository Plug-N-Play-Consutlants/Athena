"""Regression: consolidated team narrative and explicit evidence boundaries."""
from tempfile import TemporaryDirectory
from Athena.Investigation.league_recap import compose_period_report
from Athena.Investigation.recap_evidence_plan import audit_recap_evidence
rows = [
    {'team_id':'a','name':'Buyer','rank':1,'rank_change':1,'period_points':38},
    {'team_id':'b','name':'Seller','rank':3,'rank_change':-1,'period_points':29},
    {'team_id':'c','name':'Surge','rank':5,'rank_change':5,'period_points':41},
    {'team_id':'d','name':'Other','rank':8,'rank_change':-2,'period_points':22},
    {'team_id':'e','name':'Another','rank':8,'rank_change':-3,'period_points':20},
]
editorial={'trades':[{'participants':['Buyer','Seller'],'received':{'Buyer':['Player A'],'Seller':['Player B']}},
                      {'participants':['Seller','Surge'],'received':{'Seller':['Player C'],'Surge':['Player D']}}],
           'multiple_trade_teams':[('Seller',2)],'other_moves':[]}
report=compose_period_report(league_name='League',period=2,comparison={'status':'compared','teams':rows},editorial=editorial,activity={})
assert 'Buyer acquired Player A sits' not in report
assert 'Buyer' in report and 'Player A' in report and '38 points' in report
assert 'shared positions' in report and 'legitimate ties' in report
assert report.count('Buyer also acquired Player A') <= 1
with TemporaryDirectory() as d:
    audit=audit_recap_evidence(d,2)
    assert audit['player_production']['status']=='not_available_in_output'
    assert audit['trading_block']['status']=='unresolved'
print('PASS: recap pathways and evidence boundary')
