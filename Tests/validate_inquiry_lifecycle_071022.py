"""Capability census, gating, failure and completion regression."""
from pathlib import Path
import sys
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Athena.inquiry_execution import investigate, capability_catalog
from Athena.execution_registry import SPECIALISTS

assert len(capability_catalog()) == len(SPECIALISTS)
question = 'Is Auston Matthews a generational player? Evaluate evidence for and against.'
with patch('Athena.inquiry_execution.select_executable_route', return_value=('public_player_historical_stature', 'test')):
    with patch('Athena.inquiry_execution.execute_specialist', return_value={'intent':'historical'}):
        output = investigate(question, object())
        assert output['status'] == 'executed'
        assert output['completion']['state'] == 'unverified'
        assert len(output['capability_ledger']) == len(SPECIALISTS)
        assert output['capability_ledger'][0]['state'] == 'executed'
    with patch('Athena.inquiry_execution.execute_specialist', side_effect=ValueError('private detail')):
        output = investigate(question, object())
        assert output['status'] == 'failed'
        assert output['error_type'] == 'ValueError'
        assert 'private detail' not in str(output)
    with patch('Athena.inquiry_execution.execute_specialist', return_value={'inquiry_completion': {'state':'partial','requirements':['comparables']}}):
        output = investigate(question, object())
        assert output['completion']['state'] == 'partial'
with patch('Athena.inquiry_execution.select_executable_route', return_value=('', 'legacy')):
    output = investigate('unmapped', object())
    assert output['status'] == 'legacy_fallback'
    assert len(output['capability_ledger']) == len(SPECIALISTS)
print('Athena inquiry lifecycle PASS')
