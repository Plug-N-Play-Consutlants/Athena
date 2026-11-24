"""Studio historical evidence launcher should reuse the existing CLI with honest diagnostics."""
import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from Tools.athena_studio import AthenaStudio, _command_summary, _parse_evidence_periods, _evidence_refresh_summary_lines

class StudioEvidenceTests(unittest.TestCase):
    def test_period_input_is_explicit_and_bounded(self):
        self.assertEqual(_parse_evidence_periods('6, 7 8'), [6,7,8])
        for value in ('', '7 7', 'x 8', '0', '1', '2 3 4 5 6 7 8 9 10'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                _parse_evidence_periods(value)

    def test_summarize_partial_and_missing_without_credit_claim(self):
        output=json.dumps({'refresh_attempted':True,'acquisition_manifest':{'status':'partial','attempted_count':2,'periods':{'8':{'reason':'authentication unavailable'}}},'after':{'periods':[
            {'period':7,'status':'partial_numeric_reconciliation','team_count':14,'numeric_reconciled_teams':2,'total_absolute_point_difference':17,'unresolved_active_identity_count':7},
            {'period':8,'status':'missing_period_evidence','missing_components':['historical period rosters'],'next_action':'Recover period eight'}]}})
        text='\n'.join(_command_summary('Refresh & Reconcile Evidence',0,output,Path('test.log')))
        self.assertIn('Period 7: partial_numeric_reconciliation',text)
        self.assertIn('2/14',text)
        self.assertIn('Period 8: missing_period_evidence',text)
        self.assertIn('authentication unavailable',text)
        self.assertIn('NOT proof',text)
        self.assertNotIn('credited player contributions',text)

    def test_bad_json_is_not_misreported_as_reconciled(self):
        text='\n'.join(_evidence_refresh_summary_lines('warning not json'))
        self.assertIn('could not be parsed',text)

    def test_studio_action_reuses_existing_script_and_uses_thread(self):
        obj=AthenaStudio.__new__(AthenaStudio)
        obj.root=Mock()
        obj._script_command=Mock(return_value=['python','-B','diagnose_period_evidence.py'])
        obj._run_threaded=Mock()
        with patch('Tools.athena_studio.simpledialog.askstring',return_value='6 7 8'):
            obj.refresh_reconcile_evidence()
        obj._run_threaded.assert_called_once_with('Refresh & Reconcile Evidence',
            ['python','-B','diagnose_period_evidence.py','--periods','6','7','8','--refresh'])

    def test_cancel_does_not_launch(self):
        obj=AthenaStudio.__new__(AthenaStudio)
        obj.root=Mock();obj._run_threaded=Mock()
        with patch('Tools.athena_studio.simpledialog.askstring',return_value=None):
            obj.refresh_reconcile_evidence()
        obj._run_threaded.assert_not_called()

if __name__=='__main__': unittest.main()
