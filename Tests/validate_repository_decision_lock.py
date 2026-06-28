from __future__ import annotations

import importlib.util
import json
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_VERSION = "0.5.6.2.5"


def _load(path: Path):
    spec = importlib.util.spec_from_file_location("repository_decision_lock", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    print("Repository Decision Lock Validation")
    print("=" * 56)
    failures: list[str] = []
    required = [
        ROOT / "Tools" / "repository_decision_lock.py",
        ROOT / "Tools" / "doctor_repository_decision_lock.py",
        ROOT / "Tests" / "validate_repository_decision_lock.py",
        ROOT / "Tools" / "athena_studio.py",
    ]
    for path in required:
        if not path.exists():
            failures.append(f"Missing required file: {path.relative_to(ROOT).as_posix()}")
        else:
            py_compile.compile(str(path), doraise=True)
    if not failures:
        module = _load(ROOT / "Tools" / "repository_decision_lock.py")
        report = module.write_repository_decision_lock(ROOT)
        if report.version != REQUIRED_VERSION:
            failures.append(f"Version mismatch: {report.version}")
        if not report.shim_decisions:
            failures.append("Shim decisions missing.")
        if not report.duplicate_decisions:
            failures.append("Duplicate decisions missing.")
        if "Claude" not in report.report_paths.get("auditor_brief", "") and "claude" not in report.report_paths.get("auditor_brief", ""):
            failures.append("Auditor brief path missing Claude handoff marker.")
        latest = ROOT / "Reports" / "repository_decisions" / "repository_decision_lock_latest.json"
        if not latest.exists():
            failures.append("Latest decision report missing.")
        else:
            data = json.loads(latest.read_text(encoding="utf-8"))
            if data.get("version") != REQUIRED_VERSION:
                failures.append("Latest decision report version mismatch.")
            if "cleanup_candidate_duplicates" not in data.get("summary", {}):
                failures.append("Decision summary missing cleanup candidate duplicate list.")
    studio_text = (ROOT / "Tools" / "athena_studio.py").read_text(encoding="utf-8", errors="replace")
    for marker in ["Lock Repo Decisions", "show_repository_decision_lock", "doctor_repository_decision_lock.py", "validate_repository_decision_lock.py"]:
        if marker not in studio_text:
            failures.append(f"Studio missing decision lock marker: {marker}")
    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        print("Overall status: FAIL")
        return 1
    print("[PASS] decision lock tool writes JSON/Markdown/auditor brief")
    print("[PASS] shim decisions and duplicate decisions complete")
    print("[PASS] Studio action and Verify Build wiring present")
    print("Overall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
