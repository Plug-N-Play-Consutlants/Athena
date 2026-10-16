from __future__ import annotations

import unittest
import importlib.util
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import Tools.athena_studio as studio_module
from Tools.athena_studio import (
    BUILD_VALIDATION_REGISTRY,
    PROJECT_ROOT,
    AthenaStudio,
    _command_summary,
)


class StudioValidationRegistryTests(unittest.TestCase):
    def _collect_commands(self, method_name: str) -> tuple[str, list[tuple[str, list[str] | None]]]:
        studio = AthenaStudio.__new__(AthenaStudio)
        captured: dict[str, object] = {}
        studio._script_command = lambda path: ["python", path]
        studio._run_sequence_threaded = lambda label, commands: captured.update(
            label=label, commands=list(commands)
        )
        getattr(studio, method_name)()
        label = captured.get("label")
        commands = captured.get("commands")
        if not isinstance(label, str) or not isinstance(commands, list):
            self.fail(f"{method_name} did not register a command sequence")
        return label, commands

    def test_verify_build_uses_curated_release_and_capability_registry(self) -> None:
        _, commands = self._collect_commands("verify_build")
        self.assertEqual(len(commands), len(BUILD_VALIDATION_REGISTRY))
        paths = [command[1][-1] for command in commands if command[1] and not command[1][-1].startswith("Tests.test_")]
        expected_paths = [target for _, _, target, _ in BUILD_VALIDATION_REGISTRY if not target.startswith("unittest:")]
        self.assertEqual(paths, expected_paths)
        self.assertLess(len(commands), 25)
        self.assertEqual(
            {tier for tier, *_ in BUILD_VALIDATION_REGISTRY},
            {"release-critical", "targeted-regression"},
        )
        self.assertTrue(all(coverage for _, _, _, coverage in BUILD_VALIDATION_REGISTRY))
        for target in expected_paths:
            with self.subTest(path=target):
                self.assertTrue((PROJECT_ROOT / target).is_file())
        module_target = next(target for _, _, target, _ in BUILD_VALIDATION_REGISTRY if target.startswith("unittest:"))
        module_args = module_target.split(":", 1)[1].split()
        self.assertEqual(module_args[:2], ["-m", "unittest"])
        module_name = module_args[2]
        self.assertIsNotNone(importlib.util.find_spec(module_name))

    def test_standalone_everything_commands_share_acceptance_registry(self) -> None:
        _, validators = self._collect_commands("validate_everything")
        _, doctors = self._collect_commands("doctor_everything")
        validator_paths = [command[1][-1] for command in validators if command[1]]
        doctor_paths = [command[1][-1] for command in doctors if command[1]]
        self.assertIn("Tests/validate_epic4_acceptance_suite.py", validator_paths)
        self.assertIn("Tests/validate_scout_runtime_acceptance_hotfix.py", validator_paths)
        self.assertNotIn("Tools/doctor_epic4_acceptance_suite.py", doctor_paths)
        self.assertNotIn("Tools/doctor_scout_runtime_acceptance_hotfix.py", doctor_paths)
        self.assertEqual(len(doctor_paths), len(set(doctor_paths)))

    def test_only_current_studio_phase_is_used_as_a_fallback(self) -> None:
        _, validators = self._collect_commands("validate_studio")
        _, doctors = self._collect_commands("doctor_studio")
        validator_paths = [command[1][-1] for command in validators if command[1]]
        doctor_paths = [command[1][-1] for command in doctors if command[1]]
        self.assertIn("Tests/validate_athena_studio_phase2.py", validator_paths)
        self.assertIn("Tools/doctor_athena_studio_phase2.py", doctor_paths)
        self.assertFalse(any("phase1" in path or "pif_inspector" in path for path in validator_paths + doctor_paths))

    def test_bulk_workflows_do_not_repeat_a_script(self) -> None:
        for method_name in (
            "verify_build",
            "validate_everything",
            "doctor_everything",
            "validate_studio",
            "doctor_studio",
        ):
            with self.subTest(method=method_name):
                _, commands = self._collect_commands(method_name)
                paths = [command[1][-1] for command in commands if command[1]]
                self.assertEqual(len(paths), len(set(paths)))
                self.assertTrue(all(command is not None for _, command in commands))

    def test_extended_workflows_use_current_pif_and_studio_suites(self) -> None:
        _, validators = self._collect_commands("validate_everything")
        _, doctors = self._collect_commands("doctor_everything")
        validator_paths = [command[1][-1] for command in validators if command[1]]
        doctor_paths = [command[1][-1] for command in doctors if command[1]]
        self.assertIn("Tests/validate_pif1_build004.py", validator_paths)
        self.assertIn("Tools/doctor_pif1_build004.py", doctor_paths)
        self.assertIn("Tests/validate_athena_studio_phase2.py", validator_paths)
        self.assertNotIn("Tests/validate_athena_studio_phase1.py", validator_paths)
        self.assertNotIn("Tests/validate_athena_studio_pif_inspector.py", validator_paths)
        current_pif_targets = {
            "Tests/validate_pif1_build004.py",
            "Tools/doctor_pif1_build004.py",
        }
        self.assertFalse(
            any("build00" in path and path not in current_pif_targets for path in validator_paths + doctor_paths)
        )

    def test_missing_registered_command_is_a_failure(self) -> None:
        class Status:
            value = ""

            def set(self, value: str) -> None:
                self.value = value

        studio = AthenaStudio.__new__(AthenaStudio)
        console = StringIO()
        studio.write = console.write
        studio.status = Status()
        studio._record_history = lambda *args: len(args)
        studio._run_sequence("Verify Build", [("Missing check", None)])
        self.assertIn("[FAIL] Missing check: registered validation target is missing", console.getvalue())
        self.assertIn("[Verify Build] FAIL | failures=1", console.getvalue())
        self.assertEqual(studio.status.value, "Verify Build failed")

    def test_failure_summary_is_short_and_points_to_full_log(self) -> None:
        log_path = Path("Logs") / "athena_studio_commands" / "full.txt"
        output = "noise\n[FAIL] route mismatch: actual fallback\n" + ("x" * 500) + "\n"
        summary = _command_summary("Verify Build", 1, output, log_path)
        self.assertIn("[FAIL] Verify Build (exit code 1)", summary)
        self.assertIn(f"Full output: {log_path}", summary)
        self.assertTrue(any("route mismatch" in line for line in summary))
        self.assertTrue(all(len(line) < 300 for line in summary))

    def test_command_runner_persists_full_log_and_prints_summary(self) -> None:
        class Status:
            value = ""

            def set(self, value: str) -> None:
                self.value = value

        class Process:
            stdout = iter(["validator output\n", "[FAIL] route mismatch: fallback\n"])

            @staticmethod
            def wait() -> int:
                return 1

        studio = AthenaStudio.__new__(AthenaStudio)
        studio.status = Status()
        console = StringIO()
        studio.write = console.write
        studio._record_history = lambda *args: len(args)
        studio._current_version_metadata = lambda: {"ATHENA_BUILD": "test"}
        studio.refresh_status = lambda: None

        with TemporaryDirectory() as temp_dir, patch.object(
            studio_module, "STUDIO_COMMAND_LOG_DIR", Path(temp_dir)
        ), patch.object(studio_module.subprocess, "Popen", return_value=Process()):
            result = studio._run_command("Test Validator", ["python", "validator.py"])
            logs = list(Path(temp_dir).glob("*.txt"))
            self.assertEqual(result, 1)
            self.assertEqual(len(logs), 1)
            self.assertEqual(
                logs[0].read_text(encoding="utf-8"),
                "validator output\n[FAIL] route mismatch: fallback\n",
            )
            self.assertIn("[FAIL] Test Validator (exit code 1)", console.getvalue())
            self.assertNotIn("validator output", console.getvalue())


if __name__ == "__main__":
    unittest.main()
