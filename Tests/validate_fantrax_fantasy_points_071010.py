"""Regression: observed JHLPAA Fantrax scoring headers."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Athena.Investigation.standings_acquisition import normalize_standings, ensure_period_snapshots
from Athena.Investigation.standings_archive import compare_archived

def payload(period):
    return {'tableList':[{'header':{'cells':[{'key':key} for key in ('fantasyPoints','FPtsPerGame','sc','groupname','wwOrder','pointsBehindLeader')]},
        'rows':[{'fixedCells':[{'content':rank},{'teamId':team_id,'content':name}],
                 'cells':[{'content':str(points)},{'content':'3.5'},{'content':'0'}, {'content':''},{'content':'1'}, {'content':'0'}]}
                for rank,team_id,name,points in ((1,'alpha','Alpha',43 if period==1 else 49),(2,'beta','Beta',38 if period==1 else 47))
                ] if period==1 else [
                {'fixedCells':[{'content':rank},{'teamId':team_id,'content':name}],
                 'cells':[{'content':str(points)},{'content':'3.5'},{'content':'0'},{'content':''},{'content':'1'},{'content':'0'}]}
                for rank,team_id,name,points in ((1,'beta','Beta',47),(2,'alpha','Alpha',49))]}]}

first=normalize_standings(payload(1),league_id='abc',season=2026,period=1,expected_teams=2)
assert first['score_column']=='fantasyPoints'
assert [t['points'] for t in first['teams']]==[43,38]
with TemporaryDirectory() as tmp:
    result=ensure_period_snapshots(Path(tmp),league_id='abc',season=2026,period=2,expected_teams=2,fetch=payload)
    assert not result['missing_periods'],result
    assert compare_archived(Path(tmp),'abc',2026,2)['status']=='compared'
try:
    normalize_standings({'tableList':[{'header':{'cells':[{'key':'FPtsPerGame'},{'key':'pointsBehindLeader'}]},'rows':[]}]},league_id='abc',season=2026,period=1)
except ValueError as exc:
    assert 'score column unresolved' in str(exc)
else:
    raise AssertionError('must not treat relative/per-game metrics as cumulative totals')
print('PASS: observed fantasyPoints field, two-period archive, unsafe column rejection')
