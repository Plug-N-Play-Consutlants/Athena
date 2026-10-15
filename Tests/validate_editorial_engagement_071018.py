"""Regression coverage for evidence-bounded fantasy engagement copy."""
from Athena.Investigation.league_recap import investigate_period_stories, compose_period_report

comparison = {'status':'compared','teams':[
    {'name':'Active Team','team_id':'1','rank':2,'rank_change':1,'period_points':38},
    {'name':'Quiet Team','team_id':'2','rank':8,'rank_change':-2,'period_points':17},
    {'name':'Other Team','team_id':'3','rank':4,'rank_change':0,'period_points':25},
]}
records = {'records':[
    {'season_week':1,'participants':[{'participant_name':'Active Team'}]},
    {'season_week':2,'participants':[{'participant_name':'Active Team'}]},
]}
stories = investigate_period_stories(comparison, {}, {}, history=records, period=2)
assert any(s['kind']=='quiet_watch' and 'Quiet Team' in s['text'] for s in stories)
assert not any('lazy' in s['text'].lower() for s in stories)
assert 'climbed 1 place' in '\n'.join(s['text'] for s in stories)
report = compose_period_report(league_name='JHLPAA', period=2, comparison=comparison,
    editorial={}, activity={}, history=records)
assert 'The quiet corner' in report
assert 'setting lineups' in report
# Sparse source cannot establish longitudinal quietness.
assert not any(s['kind']=='quiet_watch' for s in investigate_period_stories(
    comparison, {}, {}, history={'records':records['records'][:1]}, period=2))
print('Editorial engagement regression: PASS')
