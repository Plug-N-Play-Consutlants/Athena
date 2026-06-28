from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def check(label: str, condition: bool, detail: str = "") -> bool:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}: {detail}".rstrip())
    return condition


def main() -> int:
    print("Repository Safe Cleanup Locked File Handling Doctor")
    print("=" * 64)
    failures = 0
    required = [
        ROOT / "Tools" / "repository_safe_cleanup.py",
        ROOT / "Tools" / "doctor_repository_safe_cleanup.py",
        ROOT / "Tests" / "validate_repository_safe_cleanup.py",
        ROOT / "Tools" / "athena_studio.py",
    ]
    for path in required:
        failures += 0 if check(f"required_file:{path.relative_to(ROOT).as_posix()}", path.exists(), path.relative_to(ROOT).as_posix()) else 1

    studio = (ROOT / "Tools" / "athena_studio.py").read_text(encoding="utf-8", errors="ignore")
    for marker in [
        "preview_repository_cleanup",
        "apply_repository_safe_cleanup",
        "open_repository_cleanup_report",
        "Preview Cleanup",
        "Apply Safe Cleanup",
        "Open Cleanup Report",
    ]:
        failures += 0 if check(f"studio_marker:{marker}", marker in studio, marker) else 1

    cleanup = (ROOT / "Tools" / "repository_safe_cleanup.py").read_text(encoding="utf-8", errors="ignore")
    for marker in [
        "skipped_locked",
        "locked/in-use file(s) were skipped",
        "getattr(exc, \"winerror\", None) == 32",
    ]:
        failures += 0 if check(f"cleanup_marker:{marker}", marker in cleanup, marker) else 1

    proc = subprocess.run([sys.executable, "-B", "Tools/repository_safe_cleanup.py"], cwd=ROOT, text=True, capture_output=True)
    failures += 0 if check("preview_runs", proc.returncode == 0, proc.stdout.splitlines()[-1] if proc.stdout else proc.stderr) else 1

    print("-" * 64)
    print(f"Overall status: {'PASS' if failures == 0 else 'FAIL'}")
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
