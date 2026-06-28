from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REQUIRED_VERSION = "0.5.6.2.4"


def project_root() -> Path:
    return ROOT


def main() -> int:
    root = project_root()
    reports = root / "Reports" / "repository_review"
    latest = reports / "repository_review_latest.json"
    shim_latest = reports / "shim_inventory_latest.json"
    duplicate_latest = reports / "duplicate_basename_report_latest.json"
    print("Repository Review Doctor")
    print("=" * 56)
    failures: list[str] = []
    missing_reports = [path for path in (latest, shim_latest, duplicate_latest) if not path.exists()]
    if missing_reports:
        try:
            from Tools.repository_review import write_repository_review_reports
            print("[INFO] Repository review reports missing; generating read-only review reports now.")
            write_repository_review_reports(root)
        except Exception as exc:
            failures.append(f"Could not generate missing repository review reports: {type(exc).__name__}: {exc}")
    for path in (latest, shim_latest, duplicate_latest):
        if not path.exists():
            failures.append(f"Missing report after generation attempt: {path}")
    if not failures:
        try:
            data = json.loads(latest.read_text(encoding="utf-8"))
        except Exception as exc:
            failures.append(f"Could not parse latest review report: {exc}")
            data = {}
        if data:
            if data.get("version") != REQUIRED_VERSION:
                failures.append(f"Unexpected report version: {data.get('version')}")
            if "shims" not in data or "duplicates" not in data:
                failures.append("Combined report missing shims or duplicates section.")
            for key in ("shim_count", "duplicate_basename_group_count", "shim_classifications", "duplicate_classifications"):
                if key not in data.get("summary", {}):
                    failures.append(f"Summary missing {key}.")
    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        print("Status: FAIL")
        return 1
    print(f"[PASS] latest report: {latest}")
    print(f"[PASS] shim inventory: {shim_latest}")
    print(f"[PASS] duplicate report: {duplicate_latest}")
    print("Status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
