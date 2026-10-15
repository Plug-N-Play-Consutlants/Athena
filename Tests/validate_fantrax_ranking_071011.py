"""Regression: Fantrax team identity, tied ranking, and archival comparison."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Athena.Investigation.standings_archive import validate_snapshot, save_snapshot, compare_archived
from Athena.Investigation.standings_acquisition import normalize_standings

def snapshot(period, ranks, ids=None):
    ids = ids or ['a','b','c','d']
    return {'league_id':'abc','season':2026,'period':period,'source':'fantrax_authenticated',
            'timeframe':'FROM_SEASON_START','complete':True,
            'teams':[{'team_id':tid,'rank':rank,'points':score} for tid,rank,score in zip(ids,ranks,[43,38,38,22])]}
for ranks in ([1,2,2,4],[1,2,2,3],[1,2,3,4]):
    assert validate_snapshot(snapshot(1,ranks))
for ranks in ([2,2,3,4],[1,2,2,5],[1,1,4,4]):
    try: validate_snapshot(snapshot(1,ranks))
    except ValueError: pass
    else: raise AssertionError(f'accepted malformed ranks: {ranks}')
try: validate_snapshot(snapshot(1,[1,2,2,4],['a','b','a','d']))
except ValueError as exc: assert 'duplicate team identity' in str(exc)
else: raise AssertionError('accepted duplicate team ID')
headers=['fantasyPoints','FPtsPerGame','sc','groupname','wwOrder','pointsBehindLeader']
raw={'tableList':[{'header':{'cells':[{'key':k} for k in headers]},
    'rows':[{'fixedCells':[{'content':r},{'teamId':tid,'content':tid}],
             'cells':[{'content':str(score)}]+[{'content':''} for _ in headers[1:]]}
            for r,tid,score in [(1,'a',43),(2,'b',38),(2,'c',38),(4,'d',22)]]}]}
assert len(normalize_standings(raw,league_id='abc',season=2026,period=2,expected_teams=4)['teams']) == 4
with TemporaryDirectory() as tmp:
    save_snapshot(Path(tmp),snapshot(1,[1,2,2,4]))
    save_snapshot(Path(tmp),snapshot(2,[1,2,2,4]))
    assert compare_archived(Path(tmp),'abc',2026,2)['status']=='compared'
print('PASS: tied standings, invalid gaps, unique identity, table parsing, archive comparison')
