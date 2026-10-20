from datetime import date
import importlib.util
from pathlib import Path
_spec = importlib.util.spec_from_file_location("fantrax_period_calendar", Path(__file__).resolve().parents[1] / "Athena/Investigation/fantrax_period_calendar.py")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
parse_period_calendar, acquire_period_calendar = _module.parse_period_calendar, _module.acquire_period_calendar

def test_calendar():
    payload = {'scoringPeriods': [{'period': 2, 'startDate': '2026-10-12', 'endDate': '2026-10-18'}]}
    ok = parse_period_calendar(payload, 2, today=date(2026, 10, 20))
    assert ok['status'] == 'verified_boundary' and ok['completed']
    assert parse_period_calendar(payload, 3)['status'] == 'unverified'
    assert parse_period_calendar({'scoringPeriods': payload['scoringPeriods'] * 2}, 2)['status'] == 'unverified'
    roster = parse_period_calendar({'rosterPeriods': payload['scoringPeriods']}, 2, today=date(2026, 10, 17))
    assert roster['source'].endswith('rosterPeriods') and not roster['completed']
    class Client:
        def __init__(self, **kwargs): pass
        def get(self, endpoint):
            assert endpoint == 'https://www.fantrax.com/fxea/general/getLeagueInfo'
            return payload
    assert acquire_period_calendar('test', '2026', 2, Client)['status'] == 'verified_boundary'

if __name__ == '__main__':
    test_calendar()
    print('PASS')
