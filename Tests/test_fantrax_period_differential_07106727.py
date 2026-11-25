"""Candidate data comparisons are NEVER equivalent to a verified period contract."""
from Tools.fantrax_period_probe import probe, _anonymous_fpts_signature, _period_candidate_params


def payload(points):
    return {'seasonOrProjections': [{'code':'SEASON_31n_BY_PERIOD','name':'2026-27 Reg Season - Period'}],
            'tableHeader': {'cells': [{'key':'fpts','shortName':'FPts'}]},
            'statsTable': [{'cells':[{'value':p}],'player':'SENSITIVE PLAYER'} for p in points]}


class Client:
    calls = []
    def __init__(self, **kwargs): self.calls.clear()
    def has_cookie_auth(self): return True
    def is_error_payload(self, payload): return False
    def get_player_stats(self, params):
        self.calls.append(dict(params))
        if params.get('transactionPeriod') == 8: return payload([3,4,5])
        if params.get('transactionPeriod') == 7: return payload([1,2,3])
        return payload([99,100])


def test_different_period_candidate_responses_are_still_unverified():
    result = probe(league='privateleague',season='2026',period=8,client_factory=Client)
    candidate = result['candidate_contract']
    assert candidate['different_anonymous_fpts_distributions'] is True
    assert candidate['inference']=='responses_differ_contract_still_unverified'
    assert result['status']=='period_identity_unverified'
    assert not result['verified_period_credit'] and not result['ledger_written']
    assert not candidate['credit_eligible']
    assert 'privateleague' not in str(result)
    assert 'SENSITIVE PLAYER' not in str(result)
    assert '99' not in str(candidate['comparisons'])


def test_identical_responses_do_not_establish_contract():
    class IgnoresPeriod(Client):
        def get_player_stats(self, params):
            self.calls.append(dict(params))
            return payload([5,6])
    result=probe(league='x',season='2026',period=8,client_factory=IgnoresPeriod)
    assert not result['candidate_contract']['different_anonymous_fpts_distributions']
    assert result['candidate_contract']['inference']=='no_demonstrated_period_specific_difference'
    assert not result['ledger_written']


def test_signature_exposes_no_player_values():
    signature=_anonymous_fpts_signature(payload([1,2,3]))
    assert signature['usable']
    assert set(signature)=={'usable','rows_with_fpts','fingerprint'}
    assert 'SENSITIVE PLAYER' not in str(signature)


def test_request_candidate_excludes_secrets_and_uses_source_observed_fields():
    params=_period_candidate_params('SEASON_31n_BY_PERIOD',8)
    assert params['transactionPeriod']==8
    assert set(params)=={'seasonOrProjection','timeframeTypeCode','transactionPeriod','timeStartType'}
