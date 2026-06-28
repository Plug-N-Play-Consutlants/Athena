from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REQUIRED_VERSION = "0.5.6.2.5"


def main() -> int:
    print("Repository Decision Lock Doctor")
    print("=" * 56)
    failures: list[str] = []
    try:
        from Tools.repository_decision_lock import write_repository_decision_lock
        report = write_repository_decision_lock(ROOT)
    except Exception as exc:
        print(f"[FAIL] decision lock generation: {type(exc).__name__}: {exc}")
        print("Overall status: FAIL")
        return 1
    latest = ROOT / "Reports" / "repository_decisions" / "repository_decision_lock_latest.json"
    brief = ROOT / "Reports" / "repository_decisions" / "claude_repository_audit_brief_latest.md"
    if report.version != REQUIRED_VERSION:
        failures.append(f"Unexpected decision lock version: {report.version}")
    if not latest.exists():
        failures.append(f"Missing latest decision lock report: {latest}")
    if not brief.exists():
        failures.append(f"Missing auditor brief: {brief}")
    if latest.exists():
        data = json.loads(latest.read_text(encoding="utf-8"))
        if not data.get("shim_decisions"):
            failures.append("No shim decisions recorded.")
        if not data.get("duplicate_decisions"):
            failures.append("No duplicate decisions recorded.")
        if data.get("summary", {}).get("shim_decisions", {}).get("accepted keep", 0) < 1:
            failures.append("Expected at least one accepted keep shim decision.")
    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        print("Overall status: FAIL")
        return 1
    print(f"[PASS] decision lock: {latest}")
    print(f"[PASS] auditor brief: {brief}")
    print("Overall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
