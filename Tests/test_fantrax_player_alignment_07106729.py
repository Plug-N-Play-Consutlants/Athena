"""Period comparison must not confuse row position and player identity."""
from Tools.fantrax_period_probe import _aligned_fpts_comparison, _stable_player_id, probe


def frame(items):
    return {'tableHeader': {'cells': [{'key':'rankOv'}, {'key':'fpts'}]},
            'statsTable': [{'playerId': id_, 'cells': [{}, {'content': value}]}
                           for id_,value in items],
            'seasonOrProjections': [{'code':'SEASON_31n_BY_PERIOD', 'name':'2026-27 Reg Season - Period'}]}


def test_order_independent_matched_player_comparison():
    left=frame([('playerA', '3'), ('playerB', '8')])
    right=frame([('playerB', '8'), ('playerA', '2')])
    result=_aligned_fpts_comparison(left,right)
    assert result['matched_player_count']==2
    assert result['changed_matched_player_count']==1
    assert result['matched_player_fpts_differ'] is True
    assert result['credit_eligible'] is False
    assert 'playerA' not in str(result) and 'playerB' not in str(result)


def test_unidentified_display_rows_not_matched():
    left=frame([('playerA','2')]); left['statsTable'][0].pop('playerId')
    right=frame([('playerA','5')]); right['statsTable'][0].pop('playerId')
    result=_aligned_fpts_comparison(left,right)
    assert result['matched_player_count']==0
    assert result['identity_alignment_usable'] is False
    assert _stable_player_id({'player':'Sidney Crosby', 'cells':[]}) is None


def test_conflicting_or_duplicate_ids_rejected():
    assert _stable_player_id({'playerId':'p1','player':{'playerId':'p2'}}) is None
    a=frame([('playerA','2'),('playerA','3')]); b=frame([('playerA','7')])
    result=_aligned_fpts_comparison(a,b)
    assert result['matched_player_count']==0
    assert result['requested_response_identity']['duplicate_player_ids']==1


def test_provider_probe_reports_alignment_but_never_credits():
    class Client:
        def __init__(self, **kwargs): pass
        def has_cookie_auth(self): return True
        def is_error_payload(self, response): return False
        def get_player_stats(self, params):
            fpts = '8' if params.get('transactionPeriod')==8 else '7'
            return frame([('p01', fpts)])
    result=probe(league='private',season='2026',period=8,client_factory=Client)
    alignment=result['candidate_contract']['player_alignment']
    assert alignment['matched_player_count']==1
    assert alignment['changed_matched_player_count']==1
    assert result['ledger_written'] is False
    assert result['verified_period_credit'] is False
    assert 'p01' not in str(result) and 'private' not in str(result)
