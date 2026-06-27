"""Validation for Athena Studio repository architecture governance."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    governance = importlib.import_module("Tools.repository_governance")
    audit = governance.run_governance_audit(PROJECT_ROOT)

    require(audit["file_count"] > 0, "Repository governance found no files.")
    require(audit["python_file_count"] > 0, "Repository governance found no Python files.")
    require("classification_counts" in audit, "Missing classification counts.")
    require("cleanup_plan" in audit, "Missing cleanup plan.")
    require("studio_tool_families" in audit, "Missing Studio tool family analysis.")
    require("duplicate_function_names" in audit, "Missing probable duplicate implementation analysis.")
    require("version_drift" in audit, "Missing version governance detection.")
    require("architecture_governance" in audit, "Missing architecture governance summary.")
    require("recommendations" in audit, "Missing cleanup recommendations.")
    require(hasattr(governance, "build_architecture_review_queue"), "Missing architecture review queue builder.")
    require(hasattr(governance, "cleanup_action_summary"), "Missing grouped cleanup action summary.")
    require("excluded_roots" in audit, "Missing excluded-root accounting.")
    require(".git" in audit["excluded_roots"], ".git is not excluded from governance scans.")
    require("Reports" in audit["excluded_roots"], "Generated Reports are not excluded from normal governance scans.")

    classifications = audit["classification_counts"]
    expected_review_buckets = {
        "DYNAMIC_IMPORT_REVIEW",
        "LEGACY_TOOL_REVIEW",
        "ROOT_DOC_REVIEW",
        "RUNTIME_DATA_REVIEW",
        "UNREFERENCED_SOURCE_REVIEW",
    }
    require(any(bucket in classifications for bucket in expected_review_buckets), "Review buckets were not produced.")
    require("MANUAL_REVIEW_REQUIRED" not in classifications or classifications["MANUAL_REVIEW_REQUIRED"] < audit["file_count"], "Manual review bucket was not reduced.")
    require("KEEP_ACTIVE" in classifications or "KEEP_ENTRYPOINT" in classifications, "No active/entrypoint files classified.")

    duplicate_report = governance.build_duplicate_report(audit)
    require("duplicate_content_groups" in duplicate_report, "Focused duplicate report missing content groups.")
    require("duplicate_content_summary" in duplicate_report, "Focused duplicate report missing content summary.")
    require("duplicate_function_groups" in duplicate_report, "Focused duplicate report missing function groups.")
    noisy_functions = {"__init__", "main", "to_dict", "check"}
    reported_functions = {group["function"] for group in duplicate_report["duplicate_function_groups"]}
    require(not noisy_functions.intersection(reported_functions), "Duplicate function report still includes normal Python noise.")

    recommendations = audit["recommendations"]
    require(isinstance(recommendations, list) and len(recommendations) >= 3, "Recommendation report is underpopulated.")

    queue = governance.build_architecture_review_queue(audit)
    require("category_counts" in queue, "Architecture review queue missing category counts.")
    require("items" in queue, "Architecture review queue missing item list.")
    require(queue.get("total_review_items", 0) >= 0, "Architecture review queue count invalid.")

    summary = governance.cleanup_action_summary([
        "delete_file:Scout/__pycache__/x.pyc",
        "move:CHANGE_MANIFEST_x.md->Archive/Documentation/ChangeManifests/CHANGE_MANIFEST_x.md",
        "move:RELEASE_NOTES_x.md->Archive/Documentation/ReleaseNotes/RELEASE_NOTES_x.md",
        "move:README_X.md->Archive/Documentation/LegacyReadme/README_X.md",
    ])
    require(summary.get("delete_safe") == 1, "Cleanup summary did not count delete_safe.")
    require(summary.get("archive_change_manifests") == 1, "Cleanup summary did not count change manifests.")
    require(summary.get("archive_release_notes") == 1, "Cleanup summary did not count release notes.")
    require(summary.get("archive_legacy_readmes") == 1, "Cleanup summary did not count legacy readmes.")

    version_drift = audit["version_drift"]
    require("canonical_version" in version_drift, "Version drift report missing canonical version.")
    require(version_drift.get("canonical_version") != "UNKNOWN", "Canonical version detection still returns UNKNOWN.")
    require("canonical_source" in version_drift, "Version drift report missing canonical source.")
    require("release_drift_count" in version_drift, "Version governance report missing release drift count.")
    require("version_category_counts" in version_drift, "Version governance report missing category counts.")
    require(version_drift.get("release_drift_count", 0) <= version_drift.get("drift_count", 0), "Compatibility drift count mismatch.")

    arch = audit["architecture_governance"]
    require("domains" in arch and arch["domains"], "Architecture governance missing domain counts.")
    require("recommendations" in arch and arch["recommendations"], "Architecture governance missing recommendations.")
    require("release_drift_count" in arch, "Architecture governance missing release drift count.")

    print("Repository Governance Validation")
    print("=" * 60)
    print(f"Files: {audit['file_count']}")
    print(f"Python files: {audit['python_file_count']}")
    print(f"Canonical version: {version_drift.get('canonical_version')}")
    print(f"Release drift references: {version_drift.get('release_drift_count')}")
    print(f"Architecture review surface: {audit['architecture_governance'].get('review_surface_files')}")
    print(f"Architecture review queue items: {queue.get('total_review_items')}")
    print("Classification counts:")
    for name, count in sorted(classifications.items()):
        print(f"  {name}: {count}")
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
