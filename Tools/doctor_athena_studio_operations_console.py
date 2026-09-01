"""Doctor for Athena Studio Core Workflow Console."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REQUIRED_FILES = [
    "Tools/athena_studio.py",
    "Tests/validate_athena_studio_operations_console.py",
    "Tools/doctor_athena_studio_operations_console.py",
]
REQUIRED_SYMBOLS = {
    "verify_build",
    "_status_group",
    "_build_developer_panel",
    "_toggle_developer_mode",
    "show_acceptance_explorer",
    "show_repository_audit",
    "preview_repository_cleanup",
    "apply_repository_safe_cleanup",
    "open_repository_cleanup_report",
    "export_diagnostics_logs",
    "open_reports",
    "_open_folder",
}
REQUIRED_VISIBLE_ACTIONS = {
    "🧪 Verify Build",
    "🧭 Acceptance Explorer",
    "🔎 Repository Audit",
    "🧾 Review Shims/Duplicates",
    "🔐 Lock Repo Decisions",
    "🧱 Release Hygiene",
    "🧹 Preview Cleanup",
    "✅ Apply Safe Cleanup",
    "📁 Export Logs",
    "📂 Open Reports",
}
HIDDEN_TOOL_MARKERS = {"Developer Validation", "Developer Diagnostics", "developer_panel.pack_forget"}
FORBIDDEN_BUTTON_WALL_ACTIONS = {
    "✅ Runtime", "✅ PIF", "✅ Events", "✅ Connectors",
    "✅ Capability Audit", "✅ Evidence Audit", "✅ Composition Audit",
    "🩺 Capability Audit", "🩺 Evidence Audit", "🩺 Composition Audit",
    "🩺 Repository Review", "🩺 Decision Lock",
}


def report(name: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))
    return ok


def main() -> int:
    print("Athena Studio Core Workflow Console Doctor")
    print("=" * 64)
    checks: list[bool] = []
    for rel in REQUIRED_FILES:
        checks.append(report(f"required file exists: {rel}", (PROJECT_ROOT / rel).exists(), rel))
    studio_file = PROJECT_ROOT / "Tools" / "athena_studio.py"
    text = studio_file.read_text(encoding="utf-8")
    tree = ast.parse(text)
    methods = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    checks.append(report("core workflow methods present", REQUIRED_SYMBOLS.issubset(methods), ", ".join(sorted(REQUIRED_SYMBOLS - methods))))
    checks.append(report("visible core workflow actions present", REQUIRED_VISIBLE_ACTIONS.issubset(set(a for a in REQUIRED_VISIBLE_ACTIONS if a in text)), ", ".join(sorted(REQUIRED_VISIBLE_ACTIONS))))
    toolbar_block = text[text.index("toolbar = ttk.Frame"):text.index("dev_toggle = ttk.Checkbutton")]
    order = [toolbar_block.find("🔁 Relaunch Studio"), toolbar_block.find("🔄 Reload Build"), toolbar_block.find("▶ Launch Scout")]
    checks.append(report("toolbar begins with relaunch/reload controls", all(pos >= 0 for pos in order) and order == sorted(order), "Relaunch Studio → Reload Build → Launch Scout"))
    checks.append(report("developer tools hidden by default", HIDDEN_TOOL_MARKERS.issubset(set(m for m in HIDDEN_TOOL_MARKERS if m in text)), "developer panel retained but collapsed"))
    dev_block = text[text.index("def _build_developer_panel"):text.index("def _toggle_developer_mode")]
    leaked = sorted(label for label in FORBIDDEN_BUTTON_WALL_ACTIONS if label in dev_block)
    checks.append(report("developer button wall suppressed", not leaked, ", ".join(leaked)))
    checks.append(report("legacy button wall removed from default surface", "Sync Providers" not in text and "Build Knowledge" not in text, "repository/diagnostic tiles moved out of default view"))
    checks.append(report("Studio output scrollbar retained", "output_scrollbar" in text and "yscrollcommand" in text, "scrollbar compatibility"))
    checks.append(report("diagnostics export retained", "def export_diagnostics_logs" in text and "diagnostics_export_" in text and "_open_folder" in text, "folder-first diagnostics workflow"))
    from Core.version import ATHENA_BUILD, ATHENA_VERSION, RELEASE_NAME, VERSION_SCHEMA
    checks.append(report("version schema locked", VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", VERSION_SCHEMA))
    checks.append(report("version metadata matches", ATHENA_VERSION == ATHENA_BUILD and ATHENA_VERSION >= "0.5.6.2.0", f"{ATHENA_VERSION} / {ATHENA_BUILD}"))
    checks.append(report("release name", bool(RELEASE_NAME), RELEASE_NAME))
    print("-" * 64)
    failed = len([ok for ok in checks if not ok])
    print(f"Passed: {len(checks)-failed}")
    print(f"Failed: {failed}")
    print("Overall status:", "PASS" if failed == 0 else "FAIL")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
