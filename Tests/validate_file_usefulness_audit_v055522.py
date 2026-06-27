"""Validation for v0.5.5.5.22 file usefulness audit."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def assert_true(name: str, condition: bool, detail: str, results: list[tuple[str, bool, str]]) -> None:
    results.append((name, condition, detail))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    results: list[tuple[str, bool, str]] = []

    tool_path = root / "Tools" / "audit_file_usefulness.py"
    spec = importlib.util.spec_from_file_location("audit_file_usefulness", tool_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    audit = module.run_audit(root)

    doc_path = root / "docs" / "FILE_USEFULNESS_AUDIT_v0.5.5.5.22.md"
    inventory_path = root / "docs" / "FILE_USEFULNESS_INVENTORY_v0.5.5.5.22.csv"
    cleanup_path = root / "Tools" / "cleanup_safe_repository_noise.py"

    assert_true("doc_present", doc_path.exists(), str(doc_path), results)
    assert_true("inventory_present", inventory_path.exists(), str(inventory_path), results)
    assert_true("cleanup_tool_present", cleanup_path.exists(), str(cleanup_path), results)
    assert_true("audit_has_rows", len(audit["rows"]) > 500, str(len(audit["rows"])), results)
    assert_true("all_rows_classified", all(row.get("action") for row in audit["rows"]), "every row has action", results)
    assert_true("safe_delete_is_conservative", audit["action_counts"].get("DELETE_SAFE", 0) <= 10, str(audit["action_counts"]), results)
    assert_true("historical_manifest_noise_identified", audit["action_counts"].get("ARCHIVE_CANDIDATE", 0) >= 50, str(audit["action_counts"]), results)
    assert_true("legacy_shims_identified", audit["action_counts"].get("LEGACY_SHIM_REVIEW", 0) >= 5, str(audit["action_counts"]), results)
    assert_true("no_parse_errors", audit["parse_error_count"] == 0, str(audit["parse_errors"][:5]), results)

    version_path = root / "Core" / "version.py"
    version_text = version_path.read_text(encoding="utf-8")
    assert_true("version_metadata", '0.5.5.5.22' in version_text, "Core/version.py", results)

    print("File Usefulness Audit Validation")
    print("=" * 60)
    failed = 0
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
        if not ok:
            failed += 1
    print()
    print(f"Overall status: {'PASS' if failed == 0 else 'FAIL'}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
