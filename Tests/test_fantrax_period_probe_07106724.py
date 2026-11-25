"""No unsupported period parameters and no invented fantasy credit."""
from Tools.fantrax_period_probe import _select_code, probe


def _payload():
    return {'seasonOrProjections': [
        {'code': 'SEASON_31n_BY_PERIOD', 'name': '2026-27 Reg Season - Period'},
        {'code': 'SEASON_31n_YEAR_TO_DATE', 'name': '2026-27 Reg Season - YTD'},
        {'code': 'SEASON_31l_BY_PERIOD', 'name': '2025-26 Reg Season - Period'},
    ], 'statsTable': [{'cells': [{'value': 'PRIVATE PLAYER'}]}],
       'tableHeader': {'cells': [{'key': 'fpts', 'shortName': 'FPts'}]}}


class FakeClient:
    calls = []
    def __init__(self, **kwargs):
        self.calls.clear()
    def has_cookie_auth(self): return True
    def get_player_stats(self, params):
        self.calls.append(dict(params))
        return _payload()
    def is_error_payload(self, payload): return False


def test_discovers_correct_season_only():
    assert _select_code([{'code': 'SEASON_31n_BY_PERIOD', 'name': '2026-27 Reg Season - Period'}], '2026') == 'SEASON_31n_BY_PERIOD'
    assert _select_code([{'code': 'SEASON_31l_BY_PERIOD', 'name': '2025-26 Reg Season - Period'}], '2026') is None


def test_probe_cannot_publish_ytd_or_guess_period():
    report = probe(league='testleague', season='2026', period=8, client_factory=FakeClient)
    assert report['status'] == 'period_identity_unverified'
    assert report['verified_period_credit'] is False and report['ledger_written'] is False
    assert FakeClient.calls[:2] == [{}, {'seasonOrProjection': 'SEASON_31n_BY_PERIOD'}]
    assert [c['transactionPeriod'] for c in FakeClient.calls[2:]] == [8, 7]
    assert report['candidate_contract']['credit_eligible'] is False
    serialized = str(report)
    assert 'PRIVATE PLAYER' not in serialized
    assert 'testleague' not in serialized
    assert 'FPts' in serialized


def test_no_auth_does_not_call_api():
    class NoAuth(FakeClient):
        def has_cookie_auth(self): return False
    report = probe(league='testleague', season='2026', period=8, client_factory=NoAuth)
    assert report['status'] == 'authentication_unavailable'
    assert not NoAuth.calls
