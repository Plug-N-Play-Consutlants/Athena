"""Offline regression for documented Fantrax historical table contract."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Athena.Investigation.standings_acquisition import normalize_standings, ensure_period_snapshots
from Athena.Investigation.standings_archive import compare_archived
from Providers.Fantrax.fantrax_client import FantraxClient

calls=[]
client=object.__new__(FantraxClient)
client.fxpa_request=lambda request: calls.append(request) or {}
client.get_standings(2)
assert calls[-1]['data']=={'timeframeType':'BY_PERIOD','timeStartType':'FROM_SEASON_START','period':2}
client.get_standings(2,only_period=True)
assert calls[-1]['data']['timeStartType']=='PERIOD_ONLY'

def payload(period):
    return {'tableList':[{'header':{'cells':[{'key':'win'},{'key':'points'},{'key':'pointsFor'}]},
        'rows':[{'fixedCells':[{'content':1 if period==1 else 2},{'teamId':'alpha','content':'Alpha'}],
                 'cells':[{'content':'2'},{'content':str(43 if period==1 else 51)},{'content':'999'}]},
                {'fixedCells':[{'content':2 if period==1 else 1},{'teamId':'beta','content':'Beta'}],
                 'cells':[{'content':'1'},{'content':str(38 if period==1 else 57)},{'content':'888'}]}]}]}
assert normalize_standings(payload(1),league_id='abc',season=2026,period=1,expected_teams=2)['teams'][0]['points']==43
with TemporaryDirectory() as d:
    result=ensure_period_snapshots(Path(d),league_id='abc',season=2026,period=2,expected_teams=2,fetch=payload)
    assert result['missing_periods']==[],result
    assert compare_archived(Path(d),'abc',2026,2)['status']=='compared'
try:
    normalize_standings({'tableList':[{'header':{'cells':[{'key':'pointsFor'}]},'rows':[]}]},league_id='abc',season=2026,period=1)
except ValueError as e:
    assert 'score column unresolved' in str(e)
else:
    raise AssertionError('ambiguous scoring must be rejected')
print('PASS: historical request contract, table extraction, canonical archive, ambiguous score rejection')
