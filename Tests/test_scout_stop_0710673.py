"""Regression tests for Scout Windows relative-launch ownership verification."""
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock

FILE = Path(__file__).resolve().parents[1] / 'Scout' / 'stop_scout_windows.py'
spec = importlib.util.spec_from_file_location('scout_stop_0710673', FILE)
stop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stop)

class TestStopOwnership(unittest.TestCase):
    def _run(self, command, pid=11060, exe=r'C:\Python314\python.exe', http_pid=None, http_root=None, http_exe=None):
        root = str(stop.ROOT.resolve())
        payload = {'app': 'Scout', 'runtime_provenance': {
            'project_root': root if http_root is None else http_root,
            'process_id': pid if http_pid is None else http_pid,
            'python_executable': exe if http_exe is None else http_exe}}
        response = MagicMock()
        response.__enter__.return_value = io.BytesIO(json.dumps(payload).encode())
        process = MagicMock(returncode=0, stdout=exe+'\n'+command+'\n')
        with patch.object(stop.subprocess, 'run', return_value=process), patch.object(stop.urllib.request, 'urlopen', return_value=response):
            return stop.is_scout_process(str(pid), {8765})

    def test_legacy_launch_matches_own_runtime(self):
        ok, detail = self._run(r'C:\Python314\python.exe -B launch.py')
        self.assertTrue(ok, detail)

    def test_legacy_other_pid_refused(self):
        ok, _ = self._run(r'C:\Python314\python.exe -B launch.py', http_pid=54321)
        self.assertFalse(ok)

    def test_legacy_other_executable_refused(self):
        ok, _ = self._run(r'C:\Python314\python.exe -B launch.py', http_exe=r'C:\Others\python.exe')
        self.assertFalse(ok)

    def test_legacy_other_root_refused(self):
        ok, _ = self._run(r'C:\Python314\python.exe -B launch.py', http_root='/totally/different/repository')
        self.assertFalse(ok)

    def test_unrelated_python_refused(self):
        ok, _ = self._run(r'C:\Python314\python.exe -B unrelated.py')
        self.assertFalse(ok)

    def test_legacy_no_port_refused(self):
        proc = MagicMock(returncode=0, stdout=r'C:\Python314\python.exe'+'\n'+r'C:\Python314\python.exe -B launch.py'+'\n')
        with patch.object(stop.subprocess, 'run', return_value=proc):
            ok, _ = stop.is_scout_process('11060')
        self.assertFalse(ok)

    def test_studio_launch_uses_absolute_path(self):
        source = (FILE.parents[1] / 'Tools' / 'athena_studio.py').read_text()
        self.assertIn('return [self._python(), "-B", str(script.resolve())]', source)

if __name__ == '__main__': unittest.main()
