"""Offline regression for evidence recovery and source failures."""
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Athena.evidence_reconciliation import reconcile_evidence
from Athena.request_execution import AthenaRequest, execute_request
from Athena.execution_registry import Specialist


def case(record, missing, error=None):
    player = {'subject': {'entity_id': 'player:test', 'name': 'Test Player'},
              'official_player_record': {}, 'missing': list(missing)}
    bundle = {'status': 'partial', 'sources': [], 'missing': list(missing), 'player': player}
    answer = {'intent': 'public_player_investigation', 'natural_language_response': 'Observed facts',
              'inquiry_completion': {'state': 'complete', 'requirements': [{'name': 'production', 'state': 'supported'}]},
              'developer': {'request_evidence': player}}
    if record:
        player['official_player_record'] = record
        player['fallback_source'] = 'official_nhl_club_stats'
    if error:
        player['club_stats_fallback_error'] = error
    return bundle, answer

valid = {'statistical_evidence': {'source': 'official_nhl_club_stats', 'target_season': 20262027,
         'season_series': [{'season': 20262027, 'gp': 5, 'points': 4}]}}
for record, missing, error, expected_missing, expected_sources, state in [
    (valid, ['official_nhl_player_record'], None, [], ['official_nhl_club_stats'], 'complete'),
    (valid, ['official_nhl_player_record','dated_identity_matched_player_news'], None,
     ['dated_identity_matched_player_news'], ['official_nhl_club_stats'], 'partial'),
    (None, ['official_nhl_player_record'], 'TimeoutError', ['official_nhl_player_record'], [], 'partial'),
    ({'statistical_evidence': {'source': 'official_nhl_club_stats', 'season_series': []}},
     ['official_nhl_player_record'], None, ['official_nhl_player_record'], [], 'partial'),
]:
    bundle, answer = case(record, missing, error)
    with patch('Athena.intent_resolution.select_executable_route', return_value=('probe','test')), \
         patch('Athena.execution_registry.SPECIALISTS', {'probe': Specialist('probe','test.module','handler','public')}), \
         patch('Athena.execution_registry.execute_specialist', return_value=answer), \
         patch('Athena.evidence_bundle.build_request_evidence', return_value=bundle):
        output = execute_request(AthenaRequest('Probe', mode='public', context=SimpleNamespace()))
    diag = output['developer']['inquiry_execution_trace']
    assert diag['evidence']['missing'] == expected_missing, diag
    assert diag['evidence']['sources'] == expected_sources, diag
    assert diag['result']['completion_state'] == state, diag
    assert output['developer']['inquiry_completion']['state'] == state
    if error:
        assert diag['evidence']['reconciliation']['acquisition_failures'][0]['error_type'] == error
print('Evidence reconciliation PASS')
