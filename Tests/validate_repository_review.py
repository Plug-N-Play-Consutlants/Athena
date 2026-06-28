from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REQUIRED_VERSION = "0.5.6.2.4"


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location("repository_review", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    root = project_root()
    failures: list[str] = []
    review_path = root / "Tools" / "repository_review.py"
    studio_path = root / "Tools" / "athena_studio.py"
    doctor_path = root / "Tools" / "doctor_repository_review.py"
    print("Repository Review Validation")
    print("=" * 56)
    for path in (review_path, studio_path, doctor_path):
        if not path.exists():
            failures.append(f"Missing required file: {path.relative_to(root).as_posix()}")
    if not failures:
        module = _load_module(review_path)
        report = module.write_repository_review_reports(root)
        if report.version != REQUIRED_VERSION:
            failures.append(f"Review version mismatch: {report.version}")
        if not report.shims:
            failures.append("Shim inventory is empty; expected current root shim modules to be reviewed.")
        if not report.duplicates:
            failures.append("Duplicate basename report is empty; expected duplicate basename groups to be reviewed.")
        if report.summary.get("non_standard_duplicate_basename_group_count") != 32:
            failures.append(f"Expected 32 non-standard duplicate groups from repository audit; got {report.summary.get('non_standard_duplicate_basename_group_count')}.")
        for item in report.shims:
            if not item.classification or not item.rationale or not item.target_module:
                failures.append(f"Incomplete shim classification: {item.path}")
        for item in report.duplicates:
            if not item.classification or not item.rationale or not item.package_owners:
                failures.append(f"Incomplete duplicate classification: {item.basename}")
        latest = root / "Reports" / "repository_review" / "repository_review_latest.json"
        if not latest.exists():
            failures.append("Latest combined repository review report was not written.")
        else:
            data = json.loads(latest.read_text(encoding="utf-8"))
            if data.get("version") != REQUIRED_VERSION:
                failures.append("Latest combined report version mismatch.")
    studio_text = studio_path.read_text(encoding="utf-8", errors="replace") if studio_path.exists() else ""
    required_markers = [
        "Review Shims/Duplicates",
        "show_repository_review",
        "doctor_repository_review.py",
        "validate_repository_review.py",
    ]
    for marker in required_markers:
        if marker not in studio_text:
            failures.append(f"Studio missing marker/wiring: {marker}")
    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        print("Overall status: FAIL")
        return 1
    print("[PASS] review tool loads and writes reports")
    print("[PASS] shim inventory classifications complete")
    print("[PASS] duplicate basename classifications complete")
    print("[PASS] Studio action and Verify Build wiring present")
    print("Overall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
