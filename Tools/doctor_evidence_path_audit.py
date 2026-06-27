"""Doctor for the Evidence Path Audit artifact."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "EVIDENCE_PATH_AUDIT_v0.5.5.5.19.md"
STRUCTURE_DOC = ROOT / "docs" / "PROGRAM_STRUCTURE_DIRECTION_v0.5.5.5.19.md"
VERSION_FILE = ROOT / "Core" / "version.py"
REQUIRED_SECTIONS = [
    "## Actual prompt-to-answer path",
    "## Evidence path matrix",
    "## Public player profile path",
    "## Public team analysis path",
    "## Live event/trade path",
    "## Draft/prospect path",
    "## Runtime orchestration path",
    "## Redundancy and consolidation findings",
    "## Recommended next engineering sequence",
]
REQUIRED_FINDINGS = [
    "No canonical Evidence Request Contract",
    "Runtime orchestration is diagnostic",
    "Event intelligence modules are underused",
    "Team/player public answers are seed-heavy",
    "Draft/prospect intelligence is a true source gap",
]


def check(name: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name}: {detail}")
    return passed


def main() -> int:
    print("Evidence Path Audit Doctor")
    print("=" * 64)
    failures = 0
    failures += 0 if check("audit_doc_exists", DOC.exists(), str(DOC)) else 1
    failures += 0 if check("structure_doc_exists", STRUCTURE_DOC.exists(), str(STRUCTURE_DOC)) else 1
    text = DOC.read_text(encoding="utf-8") if DOC.exists() else ""
    structure = STRUCTURE_DOC.read_text(encoding="utf-8") if STRUCTURE_DOC.exists() else ""
    for section in REQUIRED_SECTIONS:
        failures += 0 if check(f"section:{section}", section in text) else 1
    for finding in REQUIRED_FINDINGS:
        failures += 0 if check(f"finding:{finding}", finding in text) else 1
    failures += 0 if check("actual_route_order_present", "route_question(..., mode=\"public\")" in text) else 1
    failures += 0 if check("program_structure_target_present", "src/athena_engine/" in structure) else 1
    version = VERSION_FILE.read_text(encoding="utf-8") if VERSION_FILE.exists() else ""
    failures += 0 if check("version_metadata", "0.5.5.5.19" in version, "Core/version.py") else 1
    print("-" * 64)
    print("Overall status:", "PASS" if failures == 0 else "FAIL")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
