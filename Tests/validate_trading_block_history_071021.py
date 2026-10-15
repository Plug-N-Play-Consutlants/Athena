from __future__ import annotations
import tempfile
from pathlib import Path
from Athena.Investigation.trading_block_history import compare_snapshots, store_snapshot, validate_snapshot


def test_trading_block_history():
    a = dict(status='complete', authenticated=True, league_id='L', season=2026, observed_at='2026-10-13T12:00:00Z', teams=[{'team_id':'1','block':{'wanted_positions':['D']}}])
    b = dict(a, observed_at='2026-10-14T12:00:00Z', teams=[{'team_id':'1','block':{'wanted_positions':['C']}}])
    assert compare_snapshots(a,b)[0]['kind'] == 'block_changed'
    assert compare_snapshots(a,a) == []
    with tempfile.TemporaryDirectory() as tmp:
        first = store_snapshot(a,tmp)
        assert first.exists() and store_snapshot(a,tmp) == first
        assert store_snapshot(b,tmp) != first
    for invalid in [dict(a,authenticated=False),dict(a,status='partial'),dict(a,teams=[{'name':'Only Name'}])]:
        try: validate_snapshot(invalid)
        except ValueError: pass
        else: raise AssertionError('invalid observation accepted')
    try: compare_snapshots(a,dict(b,league_id='OTHER'))
    except ValueError: pass
    else: raise AssertionError('cross-league comparison accepted')

if __name__ == '__main__':
    test_trading_block_history()
    print('PASS trading block snapshot safety and change detection')
