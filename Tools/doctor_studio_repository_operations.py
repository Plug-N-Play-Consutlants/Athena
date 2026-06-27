"""Doctor for compact Studio repository operations workflow."""
from __future__ import annotations

import ast
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT / "Tools" / "athena_studio.py"
VERSION = ROOT / "Core" / "version.py"


def _version_value(name: str) -> str:
    tree = ast.parse(VERSION.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        return node.value.value
    return ""


def check(name: str, ok: bool, detail: str, rows: list[tuple[str, bool, str]]) -> None:
    rows.append((name, ok, detail))


def main() -> int:
    rows: list[tuple[str, bool, str]] = []
    text = STUDIO.read_text(encoding="utf-8")
    tree = ast.parse(text)
    methods = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}

    try:
        py_compile.compile(str(STUDIO), doraise=True)
        compiled = True
        detail = str(STUDIO)
    except Exception as exc:  # pragma: no cover
        compiled = False
        detail = str(exc)

    check("studio_compiles", compiled, detail, rows)
    for method in [
        "audit_file_usefulness",
        "preview_safe_repository_cleanup",
        "apply_safe_repository_cleanup",
        "open_audit_reports",
    ]:
        check(f"method_present:{method}", method in methods, method, rows)
    check("repository_group_present", '"Repository"' in text, "Repository section", rows)
    check("file_audit_button_present", "📊 File Audit" in text, "Studio button", rows)
    check("cleanup_preview_button_present", "🧹 Cleanup Preview" in text, "Studio button", rows)
    check("apply_safe_cleanup_button_present", "🗑️ Apply Safe Cleanup" in text, "Studio button", rows)
    check("system_status_compact", "Render a compact System Status strip" in text and "status-cards" not in text, "large card grid removed", rows)
    check("startup_runtime_audit_disabled_by_default", '"auto_runtime_audit_on_start": False' in text, "no noisy automatic audit", rows)
    check("audit_tool_no_system_exit_traceback", "raise SystemExit(main())" not in (ROOT / "Tools" / "audit_file_usefulness.py").read_text(encoding="utf-8"), "audit direct run returns cleanly", rows)
    check("cleanup_tool_no_system_exit_traceback", "raise SystemExit(main())" not in (ROOT / "Tools" / "cleanup_safe_repository_noise.py").read_text(encoding="utf-8"), "cleanup direct run returns cleanly", rows)
    check("version_advanced", _version_value("ATHENA_VERSION") == "0.5.5.5.22", _version_value("ATHENA_VERSION"), rows)

    print("Studio Repository Operations Doctor")
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
