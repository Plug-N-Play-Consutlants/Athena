"""No network required: canonical context, acquisition and honest unknown-contract handling."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Athena.Investigation.standings_acquisition import resolve_league_context, ensure_period_snapshots
from Athena.Investigation.standings_archive import compare_archived
from Scout.conversation.context import ScoutContext
from Scout.conversation.router import route_question

league, season = resolve_league_context({'league_id':'abc123','season':2026}, {})
assert (league, season)==('abc123',2026)
with TemporaryDirectory() as d:
    root=Path(d)
    def fetch(p):
        return {'leagueId':'abc123','scoringPeriod':p,'timeframeSpan':'FROM_SEASON_START',
                'teams':[{'teamId':'one','name':'One','rank':1 if p==1 else 2,'points':43 if p==1 else 51},
                         {'teamId':'two','name':'Two','rank':2 if p==1 else 1,'points':38 if p==1 else 57}]}
    status=ensure_period_snapshots(root,league_id=league,season=season,period=2,expected_teams=2,fetch=fetch)
    assert status['available_periods']==[1,2],status
    result=compare_archived(root,league,season,2)
    assert result['status']=='compared',result
    assert result['teams'][0]['rank_change']==-1
    assert result['teams'][1]['period_points']==19
    assert ensure_period_snapshots(root,league_id=league,season=season,period=2,expected_teams=2)['missing_periods']==[]
    failed=ensure_period_snapshots(root,league_id=league,season=season,period=3,expected_teams=2,
                                   fetch=lambda p: {'unrecognized':'shape'})
    assert failed['missing_periods']==[3] and 'unrecognized' in failed['errors'][3]

ctx=ScoutContext(league_profile={'league_id':'abc123','season':2026,'team_count':2})
q='Show me the JHLPAA standings at the end of Weeks 1 and 2. Identify which teams moved up or down.'
answer=route_question(q,ctx,mode='fantasy')
assert answer['intent']=='league_period_standings'
assert 'not configured with a league ID' not in str(answer)
assert answer['developer']['standings_acquisition']['missing_periods']==[1,2]
print('PASS: canonical league resolution, period acquisition, and evidence-gated response')
