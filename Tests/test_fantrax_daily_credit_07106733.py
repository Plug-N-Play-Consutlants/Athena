from datetime import date
from unittest.mock import patch
import pytest
from Tools.fantrax_period_probe import _daily_credit_shape, probe_daily_credit
from Providers.Fantrax.fantrax_client import FantraxClient


def _payload():
    return {'scorerMap': {'x': {'y': {'z': [{'scorer': {'scorerId': 'secret1', 'team': False}},
                                               {'scorer': {'scorerId': 'secret2', 'team': False}}]}}},
            'statsPerTeam': {'allTeamsStats': {'team_private': {'ACTIVE': {'statsMap': {
                'secret1': {'object1': '2'}, 'not_found': {'object1': '1'}, '_total': {'object1': '3'}
            }}}}}}


def test_daily_credit_private_safe_shapes():
    result = _daily_credit_shape(_payload())
    assert result['counts']['active_ids_in_scorer_map'] == 1
    assert result['counts']['active_ids_absent_from_scorer_map'] == 1
    assert result['counts']['entries_with_numeric_object1'] == 2
    assert result['credit_eligible'] is False
    assert all(secret not in str(result) for secret in ['secret1', 'secret2', 'team_private', 'not_found'])


def test_duplicate_active_across_teams_is_visible_but_not_credited():
    p = _payload()
    p['statsPerTeam']['allTeamsStats']['other'] = {'ACTIVE': {'statsMap': {'secret1': {'object1': '1'}}}}
    result = _daily_credit_shape(p)
    assert result['counts']['active_ids_on_multiple_teams'] == 1
    assert result['credit_eligible'] is False


def test_partial_or_empty_payload_fails_closed():
    for candidate in (None, {}, {'scorerMap': {}}, {'statsPerTeam': {'allTeamsStats': []}}):
        assert _daily_credit_shape(candidate)['credit_eligible'] is False


def test_probe_sends_explicit_date_and_no_ledger_write():
    calls = []
    class Client:
        def __init__(self, **kwargs): pass
        def has_cookie_auth(self): return True
        def is_error_payload(self, p): return False
        def get_live_scoring_stats(self, day):
            calls.append(day)
            return _payload()
    result = probe_daily_credit(league='private', season='2026', scoring_date='2026-11-17', client_factory=Client)
    assert calls == ['2026-11-17', '2026-11-16']
    assert result['status'] == 'response_received_unverified'
    assert result['ledger_written'] is False and result['verified_period_credit'] is False
    assert 'private' not in str(result)


def test_date_is_mandatory_and_strict():
    for x in ('', 'today', '2026-1-7', '2026-02-30', '2026-11-17T00:00:00'):
        with pytest.raises(ValueError):
            probe_daily_credit(league='x', scoring_date=x)


def test_provider_method_transmits_researched_contract():
    client = object.__new__(FantraxClient)
    calls = []
    client.fxpa_request = lambda m: calls.append(m) or {}
    client.get_live_scoring_stats('2026-11-17')
    assert calls[0]['method'] == 'getLiveScoringStats'
    assert calls[0]['data'] == {'date': '2026-11-17', 'newView': 'True', 'period': '1',
                                  'playerViewType': '1', 'sppId': '-1', 'viewType': '1'}
    with pytest.raises(ValueError):
        client.get_live_scoring_stats('2026-11-99')


def test_daily_studio_path_and_existing_dialog():
    from Tools.athena_studio import _fantrax_daily_credit_output_path
    from pathlib import Path
    from Tools import athena_studio
    assert _fantrax_daily_credit_output_path('2026-11-17').name == 'fantrax_daily_credit_2026-11-17.json'
    for bad in ('../../secrets', '2026-11-99', '2026-1-7'):
        with pytest.raises(ValueError):
            _fantrax_daily_credit_output_path(bad)
    source = Path(athena_studio.__file__).read_text(encoding='utf-8')
    dialog = source.split('    def show_fantrax_period_diagnostic(self)', 1)[1].split('    def _status_group(self',1)[0]
    assert '--scoring-date' in dialog
    assert 'text="Copy Report", command=copy_report' in dialog
    assert 'text="Run Probe", command=run_probe' in dialog
