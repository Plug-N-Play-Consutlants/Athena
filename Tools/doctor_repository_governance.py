"""Doctor for Athena Studio repository architecture governance readiness."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    governance = importlib.import_module("Tools.repository_governance")
    audit = governance.run_governance_audit(PROJECT_ROOT)
    errors: list[str] = []

    if not audit.get("file_count"):
        errors.append("repository file inventory is empty")
    if not audit.get("classification_counts"):
        errors.append("classification counts missing")
    if not audit.get("cleanup_plan"):
        errors.append("cleanup plan missing")
    if not audit.get("studio_tool_families"):
        errors.append("Studio tool family inventory missing")
    if "version_drift" not in audit:
        errors.append("version governance detection missing")
    else:
        drift = audit.get("version_drift") or {}
        if drift.get("canonical_version") == "UNKNOWN":
            errors.append("canonical version detection returned UNKNOWN")
    if ".git" not in audit.get("excluded_roots", []):
        errors.append(".git is not excluded from governance scans")
    if "Reports" not in audit.get("excluded_roots", []):
        errors.append("Reports are not excluded from normal governance scans")
    if "recommendations" not in audit:
        errors.append("cleanup recommendations missing")
    if "architecture_governance" not in audit:
        errors.append("architecture governance summary missing")

    print("Repository Governance Doctor")
    print("=" * 60)
    print(f"Root: {PROJECT_ROOT}")
    print(f"Files: {audit.get('file_count')}")
    print(f"Python files: {audit.get('python_file_count')}")
    print(f"Duplicate content groups: {audit.get('duplicate_content_count')}")
    print(f"Probable duplicate implementation groups: {audit.get('duplicate_function_name_count')}")
    drift = audit.get("version_drift") or {}
    print(f"Canonical version: {drift.get('canonical_version', 'UNKNOWN')}")
    print(f"Release drift references: {drift.get('release_drift_count', drift.get('drift_count', 0))}")
    print("Classification counts:")
    for name, count in sorted((audit.get("classification_counts") or {}).items()):
        print(f"  {name}: {count}")

    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
