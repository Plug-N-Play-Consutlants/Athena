"""Doctor for v0.5.0-drop4e41+ Studio polish integration."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    files = {
        "studio": PROJECT_ROOT / "Tools" / "athena_studio.py",
        "repository_doctor": PROJECT_ROOT / "Tools" / "doctor_repository.py",
        "studio_polish_doctor": PROJECT_ROOT / "Tools" / "doctor_studio_polish.py",
        "studio_polish_validator": PROJECT_ROOT / "Tests" / "validate_studio_polish_repository.py",
        "version": PROJECT_ROOT / "Core" / "version.py",
    }
    checks: list[tuple[str, bool, str]] = []
    for name, path in files.items():
        checks.append((f"{name}_exists", path.exists(), str(path)))
    studio = files["studio"].read_text(encoding="utf-8", errors="replace") if files["studio"].exists() else ""
    version = files["version"].read_text(encoding="utf-8", errors="replace") if files["version"].exists() else ""
    checks.extend([
        ("version_is_current_release", "0.5.1.1.0" in version or "major.epic.sprint.patch.hotfix" in version, "Core/version.py"),
        ("repository_doctor_button", "Doctor Repository" in studio, "Tools/athena_studio.py"),
        ("studio_polish_validator_button", "Validate Studio Polish" in studio, "Tools/athena_studio.py"),
        ("repository_health_audit", "Repository Health" in studio, "Tools/athena_studio.py"),
        ("browser_url_helper", "def _scout_url" in studio, "Tools/athena_studio.py"),
        ("refresh_browser_method", "def refresh_browser" in studio, "Tools/athena_studio.py"),
        ("everything_registers_repository_doctor", "doctor_repository.py" in studio, "Tools/athena_studio.py"),
        ("everything_registers_studio_polish_validator", "validate_studio_polish_repository.py" in studio, "Tools/athena_studio.py"),
    ])
    failed = [item for item in checks if not item[1]]
    print("Studio Polish Doctor Report")
    print("=" * 32)
    print(f"Overall status: {'PASS' if not failed else 'FAIL'}")
    print(f"Passed: {len(checks) - len(failed)}")
    print(f"Failed: {len(failed)}")
    print()
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
