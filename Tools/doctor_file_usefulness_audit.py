"""Doctor for AthenaEngine file usefulness audit."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def check(name: str, condition: bool, detail: str, results: list[tuple[str, bool, str]]) -> None:
    results.append((name, condition, detail))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    results: list[tuple[str, bool, str]] = []

    tool_path = root / "Tools" / "audit_file_usefulness.py"
    doc_path = root / "docs" / "FILE_USEFULNESS_AUDIT_v0.5.5.5.22.md"
    inventory_path = root / "docs" / "FILE_USEFULNESS_INVENTORY_v0.5.5.5.22.csv"
    cleanup_path = root / "Tools" / "cleanup_safe_repository_noise.py"
    version_path = root / "Core" / "version.py"

    check("tool_exists", tool_path.exists(), str(tool_path), results)
    check("doc_exists", doc_path.exists(), str(doc_path), results)
    check("inventory_exists", inventory_path.exists(), str(inventory_path), results)
    check("cleanup_tool_exists", cleanup_path.exists(), str(cleanup_path), results)

    if tool_path.exists():
        spec = importlib.util.spec_from_file_location("audit_file_usefulness", tool_path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        audit = module.run_audit(root)
        check("audit_file_count", audit["file_count"] > 500, str(audit["file_count"]), results)
        check("audit_python_file_count", audit["python_file_count"] > 300, str(audit["python_file_count"]), results)
        check("delete_safe_class_supported", "DELETE_SAFE" in tool_path.read_text(encoding="utf-8"), "classifier supports cache deletion", results)
        check("archive_candidates_detected", "ARCHIVE_CANDIDATE" in audit["action_counts"], str(audit["action_counts"]), results)
        check("legacy_review_detected", "LEGACY_SHIM_REVIEW" in audit["action_counts"], str(audit["action_counts"]), results)

    if version_path.exists():
        text = version_path.read_text(encoding="utf-8")
        check("version_advanced", 'ATHENA_VERSION = "0.5.5.5.22"' in text, "Core/version.py", results)
        check("release_name", "Studio Repository Operations Cleanup" in text, "Core/version.py", results)

    print("File Usefulness Audit Doctor")
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
