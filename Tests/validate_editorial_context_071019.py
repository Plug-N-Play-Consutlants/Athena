"""Regression: scoring success changes interpretation of transaction silence."""
from Athena.Investigation.league_recap import compose_period_report
rows = [{'name':f'Team {i}','team_id':str(i),'rank':i,'rank_change':0,'period_points':10} for i in range(1,11)]
rows[0].update(name='Scoring Leader',rank_change=5,period_points=41)
rows[1].update(name='Big Mover',rank_change=6,period_points=38)
rows[2].update(name='Quiet Struggler',rank_change=-3,period_points=8)
history={'records':[{'season_week':1,'participants':[{'participant_name':'Team 4'}]},{'season_week':2,'participants':[{'participant_name':'Team 4'}]}]}
report=compose_period_report(league_name='League',period=2,comparison={'status':'compared','teams':rows},editorial={},activity={},history=history)
assert 'Big Mover' in report and 'Scoring Leader' in report
assert 'Quiet, but producing' in report and 'Scoring Leader' in report.split('Quiet, but producing')[1]
assert 'Quiet Struggler' in report.split('The quiet corner')[1]
print('PASS: contextual silence and mover completeness')
