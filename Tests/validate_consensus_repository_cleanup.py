"""Validation for v0.5.5.5.26 Consensus Repository Cleanup."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def record(rows: list[tuple[str, bool, str]], name: str, ok: bool, detail: str = "") -> None:
    rows.append((name, bool(ok), detail))


def run(rel: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-B", str(ROOT / rel), *args], cwd=str(ROOT), text=True, capture_output=True, timeout=60)


def main() -> int:
    rows: list[tuple[str, bool, str]] = []
    from Core.version import ATHENA_BUILD, ATHENA_VERSION, RELEASE_NAME
    record(rows, "athena_version_at_least_cleanup", tuple(map(int, ATHENA_VERSION.split("."))) >= (0, 5, 5, 5, 26), ATHENA_VERSION)
    record(rows, "athena_build", ATHENA_BUILD == ATHENA_VERSION, ATHENA_BUILD)
    record(rows, "release_name_available", bool(RELEASE_NAME), RELEASE_NAME)
    for path in [
        "Tools/apply_consensus_repository_cleanup.py",
        "Tools/doctor_consensus_repository_cleanup.py",
        "Tests/validate_consensus_repository_cleanup.py",
    ]:
        record(rows, f"required_file:{path}", (ROOT / path).exists(), path)
    preview = run("Tools/apply_consensus_repository_cleanup.py")
    record(rows, "cleanup_preview_runs", preview.returncode == 0, (preview.stdout + preview.stderr)[-1200:])
    doctor = run("Tools/doctor_consensus_repository_cleanup.py")
    record(rows, "cleanup_doctor_passes", doctor.returncode == 0, (doctor.stdout + doctor.stderr)[-2000:])
    import build_engine
    record(rows, "build_engine_validate_pipeline", build_engine.validate_pipeline() == [], str(build_engine.validate_pipeline()))
    failed = [row for row in rows if not row[1]]
    print("Consensus Repository Cleanup Validation")
    print("=" * 64)
    for name, ok, detail in rows:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"\nOverall status: {'PASS' if not failed else 'FAIL'}")
    print(f"Passed: {len(rows) - len(failed)}")
    print(f"Failed: {len(failed)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
