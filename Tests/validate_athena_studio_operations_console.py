"""Validate Athena Studio Core Workflow Console cleanup."""
from __future__ import annotations

import ast
import py_compile
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT / "Tools" / "athena_studio.py"
VERSION = ROOT / "Core" / "version.py"

REQUIRED_METHODS = {
    "verify_build",
    "_status_group",
    "_build_developer_panel",
    "_toggle_developer_mode",
    "validate_everything",
    "doctor_everything",
    "show_acceptance_explorer",
    "show_repository_audit",
    "preview_repository_cleanup",
    "apply_repository_safe_cleanup",
    "open_repository_cleanup_report",
    "export_diagnostics_logs",
    "open_reports",
    "_open_folder",
}
REQUIRED_MARKERS = [
    "Athena Studio Core Workflow Console",
    "Core Workflow",
    "Developer Mode",
    "default path: Relaunch Studio if needed → Reload Build → Verify Build → Repository Audit → Review Shims/Duplicates → Lock Repo Decisions → Release Hygiene → Preview Cleanup → Apply Safe Cleanup → Acceptance Explorer → Export Logs",
]
DEFAULT_ACTIONS = [
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
]
DEVELOPER_ACTIONS = [
    "Developer Validation",
    "Developer Diagnostics",
    "✅ Validate Everything",
    "🩺 Doctor Everything",
    "🩺 Studio Health",
    "📁 Export Diagnostics Logs",
]
FORBIDDEN_BUTTON_WALL_ACTIONS = [
    "✅ Runtime",
    "✅ PIF",
    "✅ Events",
    "✅ Connectors",
    "✅ Capability Audit",
    "✅ Evidence Audit",
    "✅ Composition Audit",
    "🩺 Capability Audit",
    "🩺 Evidence Audit",
    "🩺 Composition Audit",
    "🩺 Repository Review",
    "🩺 Decision Lock",
]
REMOVED_DEFAULT_SURFACE = [
    "Sync Providers",
    "Build Knowledge",
    "Build Intelligence",
    "Capability Registry",
    "Execution Trace",
    "Capability Audit",
    "Evidence Audit",
    "Composition Audit",
    "Explainability",
    "File Audit",
    "Architecture",
    "Review Queue",
    "Identity Graph",
    "Event Pipeline",
    "Scout Diagnostics",
    "History",
    "Bundle",
]


def _version_value(name: str) -> str:
    tree = ast.parse(VERSION.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        return node.value.value
    return ""


def _version_at_least(value: str, minimum: str) -> bool:
    def parse(v: str) -> tuple[int, int, int, int, int]:
        nums = [int(x) if x.isdigit() else 0 for x in v.split(".")[:5]]
        while len(nums) < 5:
            nums.append(0)
        return tuple(nums)  # type: ignore[return-value]
    return parse(value) >= parse(minimum)


def main() -> int:
    print("Athena Studio Core Workflow Console Validation")
    print("=" * 64)
    failures: list[str] = []
    if not STUDIO.exists():
        failures.append("Tools/athena_studio.py is missing")
    else:
        print(f"[PASS] studio file exists: {STUDIO}")
        try:
            py_compile.compile(str(STUDIO), doraise=True)
            print("[PASS] studio py_compile")
        except Exception as exc:
            failures.append(f"Studio does not compile: {exc}")
        text = STUDIO.read_text(encoding="utf-8")
        tree = ast.parse(text)
        methods = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
        missing_methods = sorted(REQUIRED_METHODS - methods)
        if missing_methods:
            failures.append("Missing Core Workflow Console methods: " + ", ".join(missing_methods))
        else:
            print(f"[PASS] required Core Workflow Console methods present: {len(REQUIRED_METHODS)}")
        missing_markers = [m for m in REQUIRED_MARKERS if m not in text]
        if missing_markers:
            failures.append("Missing Core Workflow Console markers: " + ", ".join(missing_markers))
        else:
            print(f"[PASS] required Core Workflow Console markers present: {len(REQUIRED_MARKERS)}")
        missing_default = [a for a in DEFAULT_ACTIONS if a not in text]
        if missing_default:
            failures.append("Missing default core workflow actions: " + ", ".join(missing_default))
        else:
            print(f"[PASS] default core workflow actions present: {len(DEFAULT_ACTIONS)}")
        missing_dev = [a for a in DEVELOPER_ACTIONS if a not in text]
        if missing_dev:
            failures.append("Missing Developer Mode actions: " + ", ".join(missing_dev))
        else:
            print(f"[PASS] Developer Mode actions present: {len(DEVELOPER_ACTIONS)}")
        build_dev = text[text.index("def _build_developer_panel"):text.index("def _toggle_developer_mode")]
        button_wall_leaks = [a for a in FORBIDDEN_BUTTON_WALL_ACTIONS if a in build_dev]
        if button_wall_leaks:
            failures.append("Developer Mode button wall returned: " + ", ".join(button_wall_leaks))
        else:
            print("[PASS] Developer Mode button wall suppressed")
        build_ui = text[text.index("def _build_ui"):text.index("def _status_group")]
        visible_leaks = [label for label in REMOVED_DEFAULT_SURFACE if label in build_ui]
        if visible_leaks:
            failures.append("Removed actions still visible in default surface: " + ", ".join(visible_leaks))
        else:
            print("[PASS] non-core tools removed from default surface")
        if "developer_panel.pack_forget" not in text or "self.developer_mode" not in text:
            failures.append("Developer Mode does not hide/reveal the developer panel")
        else:
            print("[PASS] Developer Mode hide/reveal implementation present")
        build_ui_toolbar = text[text.index("toolbar = ttk.Frame"):text.index("dev_toggle = ttk.Checkbutton")]
        toolbar_actions = [
            build_ui_toolbar.find("🔁 Relaunch Studio"),
            build_ui_toolbar.find("🔄 Reload Build"),
            build_ui_toolbar.find("▶ Launch Scout"),
        ]
        if any(pos < 0 for pos in toolbar_actions) or toolbar_actions != sorted(toolbar_actions):
            failures.append("Toolbar order must start with Relaunch Studio, then Reload Build, then Launch Scout")
        else:
            print("[PASS] toolbar starts with Relaunch Studio → Reload Build → Launch Scout")
        if "output_scrollbar" not in text:
            failures.append("Studio output scrollbar was not preserved")
        else:
            print("[PASS] Studio output scrollbar preserved")

    version = _version_value("ATHENA_VERSION")
    scout = _version_value("SCOUT_VERSION")
    build = _version_value("ATHENA_BUILD")
    release = _version_value("RELEASE_NAME")
    if not _version_at_least(version, "0.5.6.2.0"):
        failures.append(f"Unexpected ATHENA_VERSION: {version}")
    elif scout != "v" + version or build != version:
        failures.append(f"Version metadata mismatch: {version} / {scout} / {build}")
    elif not release:
        failures.append("RELEASE_NAME missing")
    else:
        print(f"[PASS] version metadata: {version} / {scout} / {build} / {release}")

    print("-" * 64)
    if failures:
        print("Overall status: FAIL")
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1
    print("Overall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
