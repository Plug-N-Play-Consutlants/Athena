"""Protect joint scoring leaders and ambiguous standings from silent omission."""
from Athena.Investigation.league_recap import compose_period_report
rows = [
    {'name':'Bubba', 'team_id':'a','rank':5,'rank_change':5,'period_points':41},
    {'name':'Leeeroy','team_id':'b','rank':3,'rank_change':0,'period_points':38},
    {'name':'Grabner','team_id':'c','rank':2,'rank_change':1,'period_points':38},
    {'name':'Alien','team_id':'d','rank':7,'rank_change':6,'period_points':36},
    {'name':'Urban','team_id':'e','rank':8,'rank_change':-3,'period_points':20},
    {'name':'Bobby','team_id':'f','rank':8,'rank_change':-2,'period_points':22},
]
report = compose_period_report(league_name='JHLPAA',period=2,comparison={'status':'compared','teams':rows},editorial={},activity={})
for name in ('Bubba','Leeeroy','Grabner','Alien'):
    assert name in report, (name, report)
assert 'rank 8: Bobby, Urban' in report
lower_report = report.casefold()
assert 'shared positions' in lower_report
assert 'legitimate ties' in lower_report
assert 'no unsupported tiebreak is applied' in lower_report
print('PASS: scoring tie completeness and ambiguous standings disclosed')
