"""Studio operation and safe player-period contract boundary."""
from pathlib import Path
import pytest
from Tools.athena_studio import _fantrax_probe_output_path
from Tools.fantrax_period_probe import probe


def test_studio_report_path_is_local_and_deterministic():
    p = _fantrax_probe_output_path('2026', '8')
    assert p.name == 'fantrax_period_probe_2026_p08.json'
    assert p.parent.name == 'Output'


@pytest.mark.parametrize('season,period', [('../2026','8'), ('2026','../../8'), ('2026','0'), ('2026','100'), ('26','8'), ('２０２６','8')])
def test_studio_input_rejects_path_or_range_invalid(season,period):
    with pytest.raises(ValueError):
        _fantrax_probe_output_path(season,period)


def test_safe_report_explains_unverified_contract():
    class Client:
        calls=[]
        def __init__(self,**kwargs): pass
        def has_cookie_auth(self):return True
        def is_error_payload(self,data):return False
        def get_player_stats(self,params):
            self.calls.append(dict(params))
            return {'seasonOrProjections':[{'name':'2026-27 Reg Season - Period','code':'SEASON_31n_BY_PERIOD'}],
                    'statsTable':[{'cells':[{'value':'PRIVATE PLAYER'}]}],
                    'tableHeader':{'cells':[{'key':'fpts','shortName':'FPts'}]}}
    report=probe(league='secret',season='2026',period=8,client_factory=Client)
    compare=report['contract_comparison']
    assert compare['selector_sent']=='SEASON_31n_BY_PERIOD'
    assert not compare['requested_period_transmitted']
    assert not compare['response_period_identity_present']
    assert not report['ledger_written'] and not report['verified_period_credit']
    assert 'PRIVATE PLAYER' not in str(report) and 'secret' not in str(report)
