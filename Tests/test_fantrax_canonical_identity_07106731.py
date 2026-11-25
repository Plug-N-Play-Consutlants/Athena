"""Independent API schema-derived regression; no fake provider validation."""
from Tools.fantrax_period_probe import _stable_player_id, _aligned_fpts_comparison, _scorer_identity_shape, _active_team_credit_shape, probe


def _frame(pairs):
    return {'tableHeader': {'cells': [{'key': 'fpts'}]},
            'statsTable': [{'scorer': {'scorerId': name, 'team': False}, 'cells': [{'content': points}]}
                           for name, points in pairs],
            'seasonOrProjections': [{'code':'SEASON_31n_BY_PERIOD','name':'2026-27 Reg Season - Period'}]}


def test_scorer_id_matches_across_reordered_pages():
    left=_frame([('aabb','1'),('ccdd','2')]);right=_frame([('ccdd','3'),('aabb','1')])
    res=_aligned_fpts_comparison(left,right)
    assert res['matched_player_count']==2
    assert res['changed_matched_player_count']==1
    assert res['credit_eligible'] is False
    assert 'aabb' not in str(res)


def test_team_scorer_not_promoted_to_player():
    assert _stable_player_id({'scorer':{'scorerId':'team123','team':True}}) is None
    assert _stable_player_id({'scorer':{'scorerId':'aabb','team':False}})=='aabb'
    assert _stable_player_id({'playerId':'aabb','scorer':{'scorerId':'ccdd'}}) is None
    assert _stable_player_id({'scorer':{'scorerId':'aabb','team':False},'playerId':'aabb'})=='aabb'


def test_safe_identity_diagnostic():
    p=_frame([('aabb','3')]);d=_scorer_identity_shape(p)
    assert d['counts']['stable_player_id_recognized']==1
    assert 'aabb' not in str(d)


def test_team_credit_structure_is_not_credit():
    data = {'statsPerTeam': {'allTeamsStats': {
        'private_team': {'ACTIVE': {'statsMap': {
            'secret_player': {'object1': '5'}, '_totals': {'object1': '9'}
        }}}
    }}}
    report=_active_team_credit_shape(data)
    assert report['counts']['entries_with_numeric_object1']==1
    assert report['credit_eligible'] is False
    assert 'secret' not in str(report) and 'private_team' not in str(report)


def test_missing_active_credit_evidence_fails_closed():
    assert _active_team_credit_shape(_frame([('aabb','3')]))['credit_eligible'] is False


def test_probe_reports_observed_scorer_structure_without_credit():
    class Client:
        def __init__(self, **kwargs): pass
        def has_cookie_auth(self): return True
        def is_error_payload(self, response): return False
        def get_player_stats(self, params):
            return _frame([('aabb', '5' if params.get('transactionPeriod') == 8 else '2')])
    result=probe(league='private',season='2026',period=8,client_factory=Client)
    assert result['candidate_contract']['player_alignment']['matched_player_count']==1
    assert result['selected_player_identity_diagnostic']['counts']['stable_player_id_recognized']==1
    assert result['ledger_written'] is False
    assert result['verified_period_credit'] is False
    assert 'aabb' not in str(result) and 'private' not in str(result)
