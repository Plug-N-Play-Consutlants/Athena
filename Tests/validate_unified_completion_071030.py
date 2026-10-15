"""Cross-boundary completion agreement and conservative evidence reconciliation."""
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Athena.completion_assessment import assess_completion
from Athena.inquiry_execution import _completion
from Athena.request_execution import AthenaRequest, execute_request
from Athena.execution_registry import Specialist

cases = [
    ({'state': 'complete', 'requirements': [{'name':'roster','state':'supported'}]}, [], 'complete'),
    ({'state': 'partial', 'requirements': [{'name':'roster','state':'unresolved'}]}, [], 'partial'),
    ({'state': 'blocked', 'requirements': []}, [], 'blocked'),
    ({}, [], 'unverified'),
    ({'state': 'complete', 'requirements': [{'name':'roster','state':'supported'}]}, ['cap_ledger'], 'partial'),
]
for declared, missing, expected in cases:
    result = {'intent':'probe', 'natural_language_response':'Evidence assessed'}
    if declared:
        result['inquiry_completion'] = declared
    expected_result = assess_completion(result, evidence={'missing':missing})
    assert expected_result['state'] == expected, (expected, expected_result)
    if not missing:
        assert _completion(result, 'executed')['state'] == expected
    with patch('Athena.intent_resolution.select_executable_route', return_value=('probe','test')), \
         patch('Athena.execution_registry.SPECIALISTS', {'probe':Specialist('probe','test.module','handler','public')}), \
         patch('Athena.execution_registry.execute_specialist', return_value=result), \
         patch('Athena.evidence_bundle.build_request_evidence', return_value={'status':'partial' if missing else 'ready','sources':[],'missing':missing}):
        response = execute_request(AthenaRequest('Probe', mode='public', context=SimpleNamespace()))
    completion = response['developer']['inquiry_completion']
    trace = response['developer']['inquiry_execution_trace']['result']
    assert completion['state'] == trace['completion_state'] == expected
    assert completion['inquiry_answered_verified'] == trace['inquiry_completeness_verified']
    assert trace['unresolved_requirement_count'] == len(completion['unresolved_requirements'])
    if missing:
        assert missing[0] in completion['unresolved_requirements']
assert assess_completion(None, status='failed')['state'] == 'not_assessed'
print('Unified inquiry completion PASS')
