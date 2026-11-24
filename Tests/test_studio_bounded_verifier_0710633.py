"""Verifier-only regression tests, no Tk window or Scout process required."""
import importlib.util
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / 'Tools' / 'athena_studio.py'
spec = importlib.util.spec_from_file_location('studio_verifier_test', MODULE)
studio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(studio)


class TestBoundedVerifier(unittest.TestCase):
    def run_check(self, code, timeout=3, cancel=None):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'verification.log'
            status, returncode = studio._run_bounded_validation(
                [sys.executable, '-u', '-c', code], out,
                cancel or threading.Event(), timeout_seconds=timeout,
            )
            self.assertTrue(out.exists() or status == 'CANCELLED')
            return status, returncode, out.read_text() if out.exists() else ''

    def test_pass_streamed_output(self):
        status, rc, body = self.run_check("print('verifier-pass')")
        self.assertEqual((status, rc), ('PASS', 0))
        self.assertIn('verifier-pass', body)

    def test_fail_persists_output(self):
        status, rc, body = self.run_check("print('verifier-fail'); raise SystemExit(7)")
        self.assertEqual((status, rc), ('FAIL', 7))
        self.assertIn('verifier-fail', body)

    def test_timeout_stops_process(self):
        start = time.monotonic()
        status, rc, body = self.run_check("import time; print('started',flush=True); time.sleep(20)", timeout=0.65)
        self.assertEqual(status, 'TIMEOUT')
        self.assertIn('started', body)
        self.assertIn('TIMEOUT', body)
        self.assertLess(time.monotonic()-start, 6)

    def test_cancel_stops_process(self):
        cancel = threading.Event()
        def cancel_soon():
            time.sleep(.35)
            cancel.set()
        threading.Thread(target=cancel_soon, daemon=True).start()
        status, _, body = self.run_check("import time; print('started',flush=True); time.sleep(20)", timeout=10, cancel=cancel)
        self.assertEqual(status, 'CANCELLED')
        self.assertIn('cancelled', body)

    def test_pre_cancel_has_no_launch(self):
        cancel = threading.Event()
        cancel.set()
        status, _, body = self.run_check("raise RuntimeError('must not run')", cancel=cancel)
        self.assertEqual(status, 'CANCELLED')
        self.assertNotIn('must not run', body)


if __name__ == '__main__':
    unittest.main()
