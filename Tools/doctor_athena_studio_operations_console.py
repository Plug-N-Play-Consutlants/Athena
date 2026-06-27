"""Doctor for Athena Studio Operations Console."""
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
    "_status_group",
    "_build_developer_panel",
    "_toggle_developer_mode",
    "show_identity_graph_diagnostics",
    "show_event_pipeline_diagnostics",
    "export_diagnostics_logs",
    "open_reports",
    "_open_folder",
}
REQUIRED_UI_GROUPS = {"Operations", "System Status", "Diagnostics", "Developer Validators", "Developer Doctors & Tools"}


def report(name: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))
    return ok


def main() -> int:
    print("Athena Studio Operations Console Doctor")
    print("=" * 64)
    checks: list[bool] = []
    for rel in REQUIRED_FILES:
        checks.append(report(f"required file exists: {rel}", (PROJECT_ROOT / rel).exists(), rel))
    studio_file = PROJECT_ROOT / "Tools" / "athena_studio.py"
    text = studio_file.read_text(encoding="utf-8")
    tree = ast.parse(text)
    methods = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    checks.append(report("operations console methods present", REQUIRED_SYMBOLS.issubset(methods), ", ".join(sorted(REQUIRED_SYMBOLS - methods))))
    checks.append(report("routine buttons consolidated", "🩺 Doctor Everything" in text and "✅ Validate Everything" in text, "global controls retained"))
    checks.append(report("developer panel preserves individual tools", "Developer Mode" in text and "developer_panel.pack_forget" in text, "toggle + hidden panel"))
    checks.append(report("UI groups present", REQUIRED_UI_GROUPS.issubset(set(x for x in REQUIRED_UI_GROUPS if x in text)), ", ".join(sorted(REQUIRED_UI_GROUPS))))
    checks.append(report("Studio output scrollbar retained", "output_scrollbar" in text and "yscrollcommand" in text, "scrollbar compatibility"))
    checks.append(report("diagnostics folder export restored", "📁 Export Diagnostics Logs" in text and "diagnostics_export_" in text and "_open_folder" in text, "folder-first diagnostics workflow"))
    checks.append(report("reports folder button restored", "📂 Open Reports" in text and "def open_reports" in text, "manual log selection workflow"))
    from Core.version import ATHENA_BUILD, ATHENA_VERSION, RELEASE_NAME, VERSION_SCHEMA
    checks.append(report("version schema locked", VERSION_SCHEMA == "major.epic.sprint.patch.hotfix", VERSION_SCHEMA))
    checks.append(report("version metadata matches", ATHENA_VERSION == ATHENA_BUILD and ATHENA_VERSION >= "0.5.4.0.0", f"{ATHENA_VERSION} / {ATHENA_BUILD}"))
    checks.append(report("release name", bool(RELEASE_NAME), RELEASE_NAME))
    print("-" * 64)
    failed = len([ok for ok in checks if not ok])
    print(f"Passed: {len(checks)-failed}")
    print(f"Failed: {failed}")
    print("Overall status:", "PASS" if failed == 0 else "FAIL")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
