"""Bounded source metadata diagnostics; never publish incomplete NHL production."""
from datetime import datetime, timezone
from pathlib import Path
import json
from Athena.Investigation.nhl_period_production import fetch_complete_nhl_game_summary, acquire_nhl_period_production


class Capped:
    def get_stats(self, endpoint, params):
        start = max(0, params['start'])
        rows = [{'playerId':i+100000, 'gameId':42} for i in range(start, min(start+2, 5))]
        return {'total':5,'data':rows}


def test_adaptive_source_trace_is_metadata_only():
    trace=[]
    result=fetch_complete_nhl_game_summary(Capped(),'seasonId=20262027',trace=trace)
    assert len(result['data'])==5
    assert [x['offset'] for x in trace]==[0, 0, 2, 4]
    assert [x['returned_rows'] for x in trace]==[2,2,2,1]
    assert 'playerId' not in json.dumps(trace)
    assert 'seasonId' not in json.dumps(trace)


class Broken:
    def get_stats(self, endpoint, params):
        return {'total':6,'data':[]} if params['limit']!=-1 else {'total':6,'data':[{'playerId':1,'gameId':1}]}


def test_failed_fetch_writes_source_trace_without_sensitive_data(tmp_path):
    (tmp_path/'player_identity_map.json').write_text('[{"resolution_status":"resolved","fantrax_player_id":"F1","nhl_player_id":"100"}]')
    (tmp_path/'player_master.json').write_text('[{"player_id":"F1"}]')
    result=acquire_nhl_period_production(
        league_id='L123',season=2026,period=8,
        boundary={'status':'verified_boundary','boundary_kind':'scoring',
                  'start_at':'2026-11-16T05:00:00+00:00','end_at':'2026-11-23T05:00:00+00:00'},
        client_factory=Broken,output_dir=tmp_path,clock=datetime(2026,11,24,tzinfo=timezone.utc))
    assert result['verified'] is False
    assert 'source trace:' in result['reason']
    files=list(tmp_path.glob('PeriodScoringAudit/nhl_source_traces/*/*/*.json'))
    assert len(files)==1
    trace=json.loads(files[0].read_text())
    assert trace['period']==8
    assert trace['requests'][0]['returned_rows']==1
    assert trace['requests'][1]['returned_rows']==0
    assert 'cookie' not in json.dumps(trace).lower()
    assert 'Cayenne' not in json.dumps(trace)
    assert not list(tmp_path.glob('PeriodPlayerProduction/**/*.json'))
