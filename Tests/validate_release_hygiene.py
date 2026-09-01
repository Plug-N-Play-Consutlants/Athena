"""Validate Release Hygiene Foundation wiring."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.version import ATHENA_BUILD, ATHENA_VERSION, RELEASE_NAME, SCOUT_VERSION, VERSION_SCHEMA  # noqa: E402
from Tools.doctor_release_hygiene import build_report  # noqa: E402


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def main() -> int:
    checks = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ok, detail))

    pyproject = PROJECT_ROOT / "pyproject.toml"
    requirements = PROJECT_ROOT / "requirements.txt"
    workflow = PROJECT_ROOT / ".github" / "workflows" / "verify-build.yml"
    studio = PROJECT_ROOT / "Tools" / "athena_studio.py"

    check("version metadata advanced", ATHENA_VERSION >= "0.5.6.2.6", ATHENA_VERSION)
    check("release name present", bool(RELEASE_NAME), RELEASE_NAME)
    check("version schema", VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", VERSION_SCHEMA)
    check("Scout/build aligned", SCOUT_VERSION == f"v{ATHENA_VERSION}" and ATHENA_BUILD == ATHENA_VERSION, f"{SCOUT_VERSION}/{ATHENA_BUILD}")
    check("pyproject present", pyproject.exists(), "pyproject.toml")
    check("requirements present", requirements.exists(), "requirements.txt")
    check("workflow present", workflow.exists(), ".github/workflows/verify-build.yml")
    check("requests declared", "requests" in _read(pyproject) and "requests" in _read(requirements), "requests")
    check("Athena __version__ unified", "__version__ = ATHENA_VERSION" in _read(PROJECT_ROOT / "Athena" / "__init__.py"), "Athena/__init__.py")
    check("legacy doctor uses Core version", "VERSION = ATHENA_VERSION" in _read(PROJECT_ROOT / "Tools" / "doctor.py"), "Tools/doctor.py")
    check("Studio release hygiene action", "show_release_hygiene" in _read(studio) and "Release Hygiene" in _read(studio), "Tools/athena_studio.py")
    check("Verify Build includes release hygiene", "Tools/doctor_release_hygiene.py" in _read(studio) and "Tests/validate_release_hygiene.py" in _read(studio), "Tools/athena_studio.py")

    report = build_report()
    check("doctor report not failing", report.get("status") in {"pass", "warn"}, str(report.get("summary")))

    print("Release Hygiene Foundation Validation")
    print("=" * 64)
    failed = 0
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
        if not ok:
            failed += 1
    print(f"Overall status: {'FAIL' if failed else 'PASS'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
