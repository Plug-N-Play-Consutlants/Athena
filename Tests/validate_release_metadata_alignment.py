"""Validation for v0.5.5.5.26 Consensus Repository Cleanup."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def record(rows: list[tuple[str, bool, str]], name: str, condition: bool, detail: str = "") -> None:
    rows.append((name, bool(condition), detail))


def run_script(rel: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(ROOT / rel)],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=45,
    )


def main() -> int:
    rows: list[tuple[str, bool, str]] = []
    from Core.version import ATHENA_BUILD, ATHENA_VERSION, RELEASE_NAME, SCOUT_VERSION

    record(rows, "athena_version", ATHENA_VERSION == "0.5.5.5.26", ATHENA_VERSION)
    record(rows, "athena_build", ATHENA_BUILD == ATHENA_VERSION, ATHENA_BUILD)
    record(rows, "scout_version", SCOUT_VERSION == f"v{ATHENA_VERSION}", SCOUT_VERSION)
    record(rows, "release_name", RELEASE_NAME == "Consensus Repository Cleanup", RELEASE_NAME)

    scripts = [
        "Tools/doctor_release_metadata_alignment.py",
        "Tools/doctor_runtime_orchestration_observability.py",
        "Tools/doctor_scout_runtime_acceptance_hotfix.py",
        "Tools/doctor_live_event_source_integration.py",
        "Tests/validate_runtime_orchestration_observability.py",
        "Tests/validate_scout_runtime_acceptance_hotfix.py",
        "Tests/validate_live_event_source_integration.py",
    ]
    for rel in scripts:
        result = run_script(rel)
        detail = (result.stdout + "\n" + result.stderr)[-1500:]
        record(rows, f"script_pass:{rel}", result.returncode == 0, detail)

    failed = [row for row in rows if not row[1]]
    print("Consensus Repository Cleanup Metadata Validation")
    print("=" * 64)
    for name, ok, detail in rows:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"\nOverall status: {'PASS' if not failed else 'FAIL'}")
    print(f"Passed: {len(rows) - len(failed)}")
    print(f"Failed: {len(failed)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
