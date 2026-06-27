"""Validate Athena Studio Operations Console consolidation."""
from __future__ import annotations

import ast
import py_compile
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT / "Tools" / "athena_studio.py"
VERSION = ROOT / "Core" / "version.py"

REQUIRED_METHODS = {
    "_status_group",
    "_build_developer_panel",
    "_toggle_developer_mode",
    "show_identity_graph_diagnostics",
    "show_event_pipeline_diagnostics",
    "validate_everything",
    "doctor_everything",
    "export_diagnostics_logs",
    "open_reports",
    "_open_folder",
}
REQUIRED_MARKERS = [
    "Athena Studio Operations Console",
    "Developer Mode",
    "Operations",
    "System Status",
    "Diagnostics",
    "individual scripts are preserved in Developer Mode",
]
DEFAULT_ACTIONS = [
    "🔌 Sync Providers",
    "🧠 Build Knowledge",
    "🧩 Build Intelligence",
    "🩺 Doctor Everything",
    "✅ Validate Everything",
    "🔍 Runtime Health",
    "🧬 Identity Graph",
    "⚡ Event Pipeline",
]
DEVELOPER_ACTIONS = [
    "Developer Validators",
    "Developer Doctors & Tools",
    "✅ Runtime",
    "🩺 Repository",
    "📜 Scout Log",
    "📁 Export Diagnostics Logs",
    "📂 Open Reports",
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
    print("Athena Studio Operations Console Validation")
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
            failures.append("Missing Operations Console methods: " + ", ".join(missing_methods))
        else:
            print(f"[PASS] required Operations Console methods present: {len(REQUIRED_METHODS)}")
        missing_markers = [m for m in REQUIRED_MARKERS if m not in text]
        if missing_markers:
            failures.append("Missing Operations Console markers: " + ", ".join(missing_markers))
        else:
            print(f"[PASS] required Operations Console markers present: {len(REQUIRED_MARKERS)}")
        missing_default = [a for a in DEFAULT_ACTIONS if a not in text]
        if missing_default:
            failures.append("Missing default console actions: " + ", ".join(missing_default))
        else:
            print(f"[PASS] default console actions present: {len(DEFAULT_ACTIONS)}")
        missing_dev = [a for a in DEVELOPER_ACTIONS if a not in text]
        if missing_dev:
            failures.append("Missing Developer Mode actions: " + ", ".join(missing_dev))
        else:
            print(f"[PASS] Developer Mode actions present: {len(DEVELOPER_ACTIONS)}")
        if "developer_panel.pack_forget" not in text or "self.developer_mode" not in text:
            failures.append("Developer Mode does not hide/reveal the developer panel")
        else:
            print("[PASS] Developer Mode hide/reveal implementation present")
        if "output_scrollbar" not in text:
            failures.append("Studio output scrollbar was not preserved")
        else:
            print("[PASS] Studio output scrollbar preserved")

    version = _version_value("ATHENA_VERSION")
    scout = _version_value("SCOUT_VERSION")
    build = _version_value("ATHENA_BUILD")
    release = _version_value("RELEASE_NAME")
    if not _version_at_least(version, "0.5.4.0.0"):
        failures.append(f"Unexpected ATHENA_VERSION: {version}")
    elif scout != "v" + version or build != version:
        failures.append(f"Version metadata mismatch: {version} / {scout} / {build}")
    elif not release:
        failures.append(f"Missing RELEASE_NAME: {release}")
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
