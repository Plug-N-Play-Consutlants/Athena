"""Studio verification indicator semantics, independent of a GUI display."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'Tools' / 'athena_studio.py').read_text(encoding='utf-8')


class StudioIndicatorTests(unittest.TestCase):
    def test_build_runs_with_explicit_activity_indicator(self):
        self.assertIn('self.status.set("Verifying build...")', SOURCE)
        self.assertIn('self._verify_messages.put(("stage",', SOURCE)

    def test_finished_verification_returns_to_idle_and_preserves_result(self):
        self.assertIn('self.last_verification.set(f"Last verification: {value}")', SOURCE)
        tree = ast.parse(SOURCE)
        studio = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'AthenaStudio')
        drain = next(node for node in studio.body if isinstance(node, ast.FunctionDef) and node.name == '_drain_verify_messages')
        body = ast.unparse(drain)
        self.assertIn('self._verify_active = False', body)
        self.assertIn("self.status.set('Ready')", body)

    def test_scout_and_task_status_not_overloaded(self):
        tree = ast.parse(SOURCE)
        studio = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'AthenaStudio')
        refresh = next(node for node in studio.body if isinstance(node, ast.FunctionDef) and node.name == 'refresh_status')
        body = ast.unparse(refresh)
        self.assertIn('self.scout_state.set(', body)
        self.assertIn('if self._verify_active:', body)
        self.assertIn("self.status.set('Ready')", body)
        self.assertNotIn('self.status.set(f"{scout}', SOURCE)

if __name__ == '__main__':
    unittest.main()
