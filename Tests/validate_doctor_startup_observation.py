"""Guard Doctor's Studio lifecycle and approved toolbar sequence."""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
STUDIO = (ROOT / "Tools/athena_studio.py").read_text(encoding="utf-8")
DOCTOR = (ROOT / "Tools/doctor_athena_studio_operations_console.py").read_text(encoding="utf-8")
CLEANUP = (ROOT / "Tools/repository_safe_cleanup.py").read_text(encoding="utf-8")


def main() -> int:
    checks = {
        "startup schedules Doctor observation": "self.root.after(100, self._startup_cleanup_observation)" in STUDIO,
        "startup observation uses preview only": "report = run_cleanup(PROJECT_ROOT, apply=False)" in STUDIO,
        "startup Doctor reports no-file-change status": "No files changed." in STUDIO,
        "startup Doctor failure is visible": "[FAIL] Startup Cleanup Doctor observation" in STUDIO,
        "Doctor uses approved toolbar order": 'order = [toolbar_block.find("🔄 Reload Build"), toolbar_block.find("🔁 Relaunch Studio")' in DOCTOR,
        "safe cleanup retains review-only protection": 'candidate.classification != "safe"' in CLEANUP,
        "source parsable": all(ast.parse(source) for source in (STUDIO, DOCTOR, CLEANUP)),
    }
    for name, ok in checks.items():
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print("Overall status:", "PASS" if all(checks.values()) else "FAIL")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
