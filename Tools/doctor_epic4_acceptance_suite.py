"""Doctor for v0.5.0-drop4e42 Epic 4 Acceptance Suite wiring."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_BUILD, ATHENA_VERSION, SCOUT_VERSION  # noqa: E402


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
        print("Epic 4 Acceptance Suite Doctor")
        print("=" * 40)
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

    required_files = [
        "Tests/validate_epic4_acceptance_suite.py",
        "Tools/doctor_epic4_acceptance_suite.py",
        "Tools/athena_studio.py",
        "Core/version.py",
        "CHANGE_MANIFEST_v0.5.0_drop4e42_epic4_acceptance_suite.md",
    ]
    for rel in required_files:
        path = PROJECT_ROOT / rel
        report.check(path.exists(), f"required_file:{rel}", rel)

    validator_text = (PROJECT_ROOT / "Tests" / "validate_epic4_acceptance_suite.py").read_text(encoding="utf-8")
    report.check("canonical_prompt_count" in validator_text and "len(cases) >= 100" in validator_text, "acceptance_suite_100_prompt_gate")
    for category in ["players", "teams", "comparisons", "rules", "ambiguity", "fantasy_general", "event_routing", "historical"]:
        report.check(category in validator_text, f"acceptance_category:{category}")

    studio_text = (PROJECT_ROOT / "Tools" / "athena_studio.py").read_text(encoding="utf-8")
    report.check("Validate Epic 4 Acceptance" in studio_text, "studio_validation_button")
    report.check("Doctor Epic 4 Acceptance" in studio_text, "studio_doctor_button")
    report.check("validate_epic4_acceptance_suite.py" in studio_text, "studio_validate_everything_wiring")
    report.check("doctor_epic4_acceptance_suite.py" in studio_text, "studio_doctor_everything_wiring")

    return report.emit()


if __name__ == "__main__":
    raise SystemExit(main())
