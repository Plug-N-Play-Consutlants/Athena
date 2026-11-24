"""Release-gate regression checks for the Studio -> canonical sync boundary."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import importlib
sync_module = importlib.import_module("Athena.sync")
from Tools import sync_league


class SyncIntegrityTests(unittest.TestCase):
    def test_required_stage_fails_when_old_output_is_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'league_settings.json'
            path.write_text('{"league_name":"Old"}')
            step = {'id':'build_league_settings'}
            with patch.dict(sync_module._REQUIRED_STAGE_ARTIFACTS, {'build_league_settings': (path,)}):
                before = sync_module._artifact_snapshot((path,))
                with self.assertRaisesRegex(Exception, 'did not refresh'):
                    sync_module._assert_fresh_required_artifacts(step, before)
                path.write_text('{"league_name":"New, refreshed"}')
                sync_module._assert_fresh_required_artifacts(step, before)

    def test_required_stage_fails_if_artifact_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'missing.json'
            with patch.dict(sync_module._REQUIRED_STAGE_ARTIFACTS, {'build_league_settings': (path,)}):
                with self.assertRaisesRegex(Exception, 'did not refresh'):
                    sync_module._assert_fresh_required_artifacts({'id':'build_league_settings'}, {})

    def test_league_mismatch_detected(self):
        def read_fixture(path):
            if path.name == 'league_settings.json':
                return {'league_id':'league-a','league_name':'JHLPAA','season':2026}
            if path.name == 'league_profile.json':
                return {'league_id':'league-b','league_name':'JHLPAA','season':2026}
            return {}
        with patch.object(sync_module, '_read_json', side_effect=read_fixture), \
             patch.object(sync_module, 'get_workspace_value', return_value='league-a'):
            with self.assertRaisesRegex(Exception, 'identity mismatch'):
                sync_module._assert_league_identity()

    def test_studio_entry_point_rejects_misrouted_workspace(self):
        with patch.object(sync_league, 'get_workspace_value', side_effect=lambda k: {'mode':'public','provider':'Fantrax'}[k]), \
             patch.object(sync_league, 'sync') as called:
            self.assertEqual(sync_league.main(), 1)
            called.assert_not_called()

    def test_studio_entry_point_rejects_false_success(self):
        with patch.object(sync_league, 'get_workspace_value', side_effect=lambda k: {'mode':'fantasy_league','provider':'Fantrax'}[k]), \
             patch.object(sync_league, 'sync', return_value={'ok':True,'mode':'fantasy_league','provider':'Fantrax','completed_steps':[]}):
            self.assertEqual(sync_league.main(), 1)

    def test_studio_entry_point_accepts_completed_required_stages(self):
        required = [{'id': step['id'],'status':'completed','validation_status':'pass'}
                    for step in sync_league.FANTRAX_FANTASY_PIPELINE if step.get('required',True)]
        with patch.object(sync_league, 'get_workspace_value', side_effect=lambda k: {'mode':'fantasy_league','provider':'Fantrax'}[k]), \
             patch.object(sync_league, 'sync', return_value={'ok':True,'mode':'fantasy_league','provider':'Fantrax','completed_steps':required}):
            self.assertEqual(sync_league.main(), 0)

    def test_studio_sync_uses_canonical_entry_and_release_gate(self):
        from Tools.athena_studio import BUILD_VALIDATION_REGISTRY, AthenaStudio
        import inspect
        source = inspect.getsource(AthenaStudio.sync_league)
        self.assertIn('Tools/sync_league.py', source)
        self.assertTrue(any('test_sync_integrity_0710661' in entry[2] for entry in BUILD_VALIDATION_REGISTRY))

if __name__ == '__main__':
    unittest.main()

class ScoutRuntimeOwnershipTests(unittest.TestCase):
    def test_launch_does_not_trust_unverified_existing_port(self):
        from Tools.athena_studio import AthenaStudio
        import inspect
        source = inspect.getsource(AthenaStudio.launch_scout)
        self.assertIn('the process version is unverified', source)
        self.assertIn('if not self._wait_for_ports_clear():', source)
        self.assertIn('Refusing to launch an ambiguous runtime', source)
