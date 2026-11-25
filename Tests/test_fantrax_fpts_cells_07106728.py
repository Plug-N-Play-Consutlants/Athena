"""FPts decoding and diagnostics must never certify a scoring period."""
from Tools.fantrax_period_probe import (_anonymous_fpts_signature,
    _decode_number, _fpts_cell_diagnostic, probe)


def payload(points):
    return {'seasonOrProjections': [
        {'code':'SEASON_31n_BY_PERIOD','name':'2026-27 Reg Season - Period'}],
        'tableHeader': {'cells': [{'key':'rankOv'}, {'key':'fpts'}]},
        'statsTable': [{'player':'PRIVATE PLAYER', 'cells': [{}, item]}
                       for item in points]}


def test_numeric_cell_representations():
    for cell in ({'text':'1,234.5'}, {'value':{'displayValue':'-2.25'}},
                 {'rawValue':3, 'display':'3.0'}, 0, '0', {'stat':{'value':'1.25'}}):
        assert _decode_number(cell) is not None
    for cell in (True, {'text':'PRIVATE PLAYER'}, {'html':'<span>12</span>'},
                 {'value':'1', 'display':'2'}, {'value':'NaN'},
                 {'text':'1,2,3'}, {'value':{'text':'-'}}, [], None):
        assert _decode_number(cell) is None


def test_diagnostic_reports_shape_only():
    data = payload([{'text':'1,234.5','player':'SECRET'},
                    {'value':{'displayValue':'0'}}, {'html':'<span>10</span>'}])
    diag = _fpts_cell_diagnostic(data)
    assert diag['decoded_cells'] == 2
    assert diag['allowlisted_cell_field_counts'] == {'text':1,'value':1,'html':1}
    assert 'SECRET' not in str(diag) and 'PRIVATE PLAYER' not in str(diag)
    result = _anonymous_fpts_signature(data)
    assert result['usable'] and result['rows_with_fpts'] == 2
    assert set(result) == {'usable','rows_with_fpts','fingerprint'}
    assert '1234' not in str(result)


def test_conflicting_presentations_do_not_manufacture_fpts():
    data = payload([{'value':'1','display':'2'}, {'value':'unavailable'}])
    assert _anonymous_fpts_signature(data)['usable'] is False
    assert _fpts_cell_diagnostic(data)['decoded_cells'] == 0


def test_probe_uses_existing_integration_without_ledger_write():
    class Client:
        def __init__(self, **kwargs): pass
        def has_cookie_auth(self): return True
        def is_error_payload(self, response): return False
        def get_player_stats(self, params):
            value = '2' if params.get('transactionPeriod') == 8 else '1'
            return payload([{'text':value}])
    result = probe(league='private',season='2026',period=8,client_factory=Client)
    candidate = result['candidate_contract']
    assert candidate['different_anonymous_fpts_distributions'] is True
    assert candidate['signature_comparable'] is True
    assert candidate['credit_eligible'] is False
    assert result['ledger_written'] is False and result['verified_period_credit'] is False
    assert result['selected_fpts_cell_diagnostic']['decoded_cells'] == 1
    assert 'private' not in str(result)
