"""Doctor for File Usefulness version alignment.

Verifies that the File Usefulness Audit derives its report version from the
canonical Core.version metadata instead of a stale embedded cleanup label.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def add(rows: list[tuple[str, bool, str]], name: str, ok: bool, detail: str) -> None:
    rows.append((name, ok, detail))


def load_audit_module():
    audit_tool = ROOT / "Tools" / "audit_file_usefulness.py"
    spec = importlib.util.spec_from_file_location("audit_file_usefulness", audit_tool)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def main() -> int:
    rows: list[tuple[str, bool, str]] = []

    from Core.version import ATHENA_VERSION, ATHENA_BUILD, RELEASE_NAME

    add(rows, "core_version_advanced", tuple(map(int, ATHENA_VERSION.split("."))) >= (0, 5, 5, 5, 24), ATHENA_VERSION)
    add(rows, "core_build_advanced", tuple(map(int, ATHENA_BUILD.split("."))) >= (0, 5, 5, 5, 24), ATHENA_BUILD)
    add(rows, "release_name_set", bool(RELEASE_NAME), RELEASE_NAME)

    module = load_audit_module()
    add(rows, "audit_version_matches_core", module.AUDIT_VERSION == ATHENA_VERSION, module.AUDIT_VERSION)
    add(rows, "audit_has_canonical_version_function", callable(getattr(module, "canonical_version", None)), "canonical_version")

    audit = module.run_audit(ROOT)
    add(rows, "run_audit_version_matches_core", audit.get("version") == ATHENA_VERSION, str(audit.get("version")))
    add(rows, "run_audit_parse_clean", audit.get("parse_error_count") == 0, str(audit.get("parse_error_count")))
    add(rows, "core_namespace_visible_in_audit", any(row.get("path") == "Core/version.py" and row.get("action") == "KEEP_ACTIVE" for row in audit.get("rows", [])), "Core/version.py KEEP_ACTIVE")

    json_path, csv_path = module.write_outputs(audit, ROOT / "Reports" / "file_usefulness")
    add(rows, "json_filename_uses_core_version", f"file_usefulness_audit_{ATHENA_VERSION}.json" == json_path.name, json_path.name)
    add(rows, "csv_filename_uses_core_version", f"file_usefulness_inventory_{ATHENA_VERSION}.csv" == csv_path.name, csv_path.name)

    print("File Usefulness Version Alignment Doctor")
    print("=" * 60)
    failed = 0
    for name, ok, detail in rows:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
        if not ok:
            failed += 1
    print()
    print(f"Overall status: {'PASS' if failed == 0 else 'FAIL'}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
