"""Validate Studio diagnostics log export workflow restoration."""
from __future__ import annotations

import ast
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
STUDIO = ROOT / "Tools" / "athena_studio.py"


def check(results: list[tuple[str, bool, str]], name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def main() -> int:
    print("Diagnostics Log Export Workflow Validation")
    print("=" * 60)
    results: list[tuple[str, bool, str]] = []
    check(results, "studio_file_exists", STUDIO.exists(), str(STUDIO))
    try:
        py_compile.compile(str(STUDIO), doraise=True)
        check(results, "studio_compiles", True)
    except Exception as exc:
        check(results, "studio_compiles", False, str(exc))
    text = STUDIO.read_text(encoding="utf-8")
    tree = ast.parse(text)
    methods = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    for method in ["export_diagnostics_logs", "open_reports", "_open_folder"]:
        check(results, f"method_{method}", method in methods)
    for marker in ["📁 Export Diagnostics Logs", "📂 Open Reports", "diagnostics_export_", "diagnostics_manifest.json"]:
        check(results, f"marker_{marker}", marker in text)
    check(results, "exports_to_reports_subfolder", "REPORT_DIR / f\"diagnostics_export_" in text)
    check(results, "copies_latest_debug_exports", "scout_debug_export_*.txt" in text and "scout_debug_export_*.json" in text)
    check(results, "copies_studio_and_scout_logs", "athena_studio_scout.log" in text and "studio_visible_output.txt" in text)
    check(results, "opens_folder_after_export", "self._open_folder(export_dir)" in text)
    from Core.version import ATHENA_VERSION, SCOUT_VERSION, ATHENA_BUILD, RELEASE_NAME
    check(results, "version_metadata", ATHENA_VERSION == ATHENA_BUILD and SCOUT_VERSION == "v" + ATHENA_VERSION and ATHENA_VERSION >= "0.5.5.5.15", f"{ATHENA_VERSION} / {RELEASE_NAME}")
    failed = [(n,d) for n,ok,d in results if not ok]
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))
    print("-" * 60)
    print(f"Passed: {len(results)-len(failed)}")
    print(f"Failed: {len(failed)}")
    print("Overall status:", "PASS" if not failed else "FAIL")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
