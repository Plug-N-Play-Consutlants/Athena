"""Validation for v0.5.5.5.24 Studio repository operations cleanup."""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT / "Tools" / "athena_studio.py"


def add(results: list[tuple[str, bool, str]], name: str, ok: bool, detail: str) -> None:
    results.append((name, ok, detail))


def main() -> int:
    results: list[tuple[str, bool, str]] = []
    text = STUDIO.read_text(encoding="utf-8")
    tree = ast.parse(text)
    methods = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}

    add(results, "repo_buttons_present", all(marker in text for marker in ["📊 File Audit", "🧹 Cleanup Preview", "🗑️ Apply Safe Cleanup", "📂 Audit Reports"]), "repository operation controls")
    add(results, "repo_methods_present", {"audit_file_usefulness", "preview_safe_repository_cleanup", "apply_safe_repository_cleanup", "open_audit_reports"}.issubset(methods), "Studio methods")
    add(results, "large_status_grid_removed", "status-cards" not in text and "Render a compact System Status strip" in text, "compact system status")
    add(results, "startup_audit_opt_in", '"auto_runtime_audit_on_start": False' in text, "runtime audit is no longer automatic by default")

    audit_tool = ROOT / "Tools" / "audit_file_usefulness.py"
    cleanup_tool = ROOT / "Tools" / "cleanup_safe_repository_noise.py"
    add(results, "audit_tool_clean_main", "raise SystemExit(main())" not in audit_tool.read_text(encoding="utf-8"), "no Spyder SystemExit traceback")
    add(results, "cleanup_tool_clean_main", "raise SystemExit(main())" not in cleanup_tool.read_text(encoding="utf-8"), "no Spyder SystemExit traceback")

    spec = importlib.util.spec_from_file_location("audit_file_usefulness", audit_tool)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    audit = module.run_audit(ROOT)
    add(results, "audit_still_runs", audit.get("file_count", 0) > 500 and audit.get("parse_error_count") == 0, str({"files": audit.get("file_count"), "parse_errors": audit.get("parse_error_count")}))

    version_text = (ROOT / "Core" / "version.py").read_text(encoding="utf-8")
    add(results, "version_metadata", "0.5.5.5.24" in version_text and "File Usefulness Version Alignment" in version_text, "Core/version.py")

    print("Studio Repository Operations Validation")
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
