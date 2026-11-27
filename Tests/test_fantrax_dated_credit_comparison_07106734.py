from Tools.fantrax_period_probe import (_dated_credit_snapshot, _dated_credit_comparison,
    _explicit_date_markers, probe_daily_credit)


def payload(one, two, date=None):
    response = {'statsPerTeam': {'allTeamsStats': {
        'private_team': {'ACTIVE': {'statsMap': {
            'private_player_1': {'object1': str(one)},
            'private_player_2': {'object1': str(two)},
            '_total': {'object1': '999'},
        }}}
    }}, 'scorerMap': {'a': {'scorer': {'scorerId': 'private_player_1'}}}}
    if date:
        response['scoringDate'] = date
    return response


def test_dated_matched_numeric_comparison_is_private():
    result = _dated_credit_comparison(payload(4, 2), payload(1, 2))
    assert result['matched_player_team_entries'] == 2
    assert result['changed_matched_numeric_entries'] == 1
    assert result['teams_with_different_numeric_sums'] == 1
    assert result['candidate_responses_differ'] is True
    assert result['credit_eligible'] is False
    assert 'private_' not in str(result)
    assert '4' not in str(result.get('changed_matched_numeric_entries'))


def test_equal_responses_do_not_verify_date():
    r = _dated_credit_comparison(payload(1, 2), payload(1, 2))
    assert r['candidate_responses_differ'] is False
    assert r['response_date_identity_verified'] is False
    assert r['credit_eligible'] is False


def test_markers_not_date_proof():
    r = _explicit_date_markers(payload(1, 2, '2026-11-23'), '2026-11-23')
    assert r == {'fields_inspected': 1, 'exact_requested_date_matches': 1}


def test_absent_or_ambiguous_value_fails_closed():
    p = payload(1,2)
    p['statsPerTeam']['allTeamsStats']['private_team']['ACTIVE']['statsMap']['private_player_1']['object1'] = '3-4'
    records, info = _dated_credit_snapshot(p)
    assert len(records) == 1
    assert info['usable'] is False


def test_probe_requests_two_dates_and_writes_nothing():
    calls=[]
    class Client:
        def __init__(self, **kw): pass
        def has_cookie_auth(self): return True
        def is_error_payload(self, p): return False
        def get_live_scoring_stats(self, day):
            calls.append(day)
            return payload(4 if day.endswith('23') else 2, 2)
    result=probe_daily_credit(league='private_league', scoring_date='2026-11-23', client_factory=Client)
    assert calls == ['2026-11-23','2026-11-22']
    assert result['date_comparison']['changed_matched_numeric_entries'] == 1
    assert result['ledger_written'] is False and result['verified_period_credit'] is False
    assert 'private_' not in str(result)


def test_failed_control_does_not_destroy_requested_evidence():
    class Client:
        def __init__(self,**kw): pass
        def has_cookie_auth(self): return True
        def is_error_payload(self,p): return False
        def get_live_scoring_stats(self,day):
            if day == '2026-11-22': raise OSError('secret private_token')
            return payload(1,2)
    r=probe_daily_credit(league='l',scoring_date='2026-11-23',client_factory=Client)
    assert r['status']=='response_received_unverified'
    assert r['date_comparison']['status']=='control_request_failed'
    assert 'secret' not in str(r)
