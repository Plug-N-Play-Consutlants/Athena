"""Validate v0.5.0-drop4e41+ Studio polish and repository doctor integration."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_VERSION, SCOUT_VERSION, ATHENA_BUILD  # noqa: E402
from Tools.doctor_repository import repository_health  # noqa: E402


class Report:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.lines: list[str] = []

    def check(self, condition: bool, name: str, detail: str = "") -> None:
        if condition:
            self.passed += 1
            self.lines.append(f"[PASS] {name}: {detail}".rstrip())
        else:
            self.failed += 1
            self.lines.append(f"[FAIL] {name}: {detail}".rstrip())

    def emit(self) -> int:
        print("Studio Polish / Repository Health Validation Report")
        print("=" * 56)
        print(f"Overall status: {'PASS' if self.failed == 0 else 'FAIL'}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print()
        for line in self.lines:
            print(line)
        return 0 if self.failed == 0 else 1


def main() -> int:
    report = Report()
    report.check(ATHENA_VERSION == "0.5.0-drop4e42", "athena_version", ATHENA_VERSION)
    report.check(SCOUT_VERSION == "v0.5.0-drop4e42", "scout_version", SCOUT_VERSION)
    report.check(ATHENA_BUILD == "drop4e42", "athena_build", ATHENA_BUILD)

    studio_path = PROJECT_ROOT / "Tools" / "athena_studio.py"
    studio_text = studio_path.read_text(encoding="utf-8", errors="replace")
    report.check("Doctor Repository" in studio_text, "studio_doctor_repository_button_registered")
    report.check("Validate Studio Polish" in studio_text, "studio_polish_validator_button_registered")
    report.check("Repository Health" in studio_text, "runtime_audit_repository_health_section")
    report.check("validate_studio_polish_repository.py" in studio_text, "validate_everything_includes_studio_polish")
    report.check("doctor_repository.py" in studio_text, "doctor_everything_includes_repository_doctor")
    report.check("_scout_url" in studio_text and "cache_bust" in studio_text, "browser_url_helper_present")
    report.check("refresh_browser" in studio_text, "browser_refresh_path_present")

    health = repository_health()
    failed = [item for item in health["checks"] if not item[1]]
    report.check(not failed, "repository_health_checks_pass", f"failed={len(failed)}")
    obs = health["observations"]
    report.check(isinstance(obs.get("duplicate_module_filenames"), dict), "repository_duplicate_module_observation_available")
    report.check(isinstance(obs.get("empty_directories"), list), "repository_empty_directory_observation_available")

    proc = subprocess.run([sys.executable, "-B", str(PROJECT_ROOT / "Tools" / "doctor_repository.py")], cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    report.check(proc.returncode == 0, "doctor_repository_exits_zero", (proc.stdout + proc.stderr).splitlines()[0] if (proc.stdout + proc.stderr).splitlines() else "")
    report.check("Athena Repository Doctor Report" in proc.stdout, "doctor_repository_report_header")

    return report.emit()


if __name__ == "__main__":
    raise SystemExit(main())
