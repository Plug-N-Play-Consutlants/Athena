"""Validate Athena Studio Beta UI command-center polish."""
from __future__ import annotations

import ast
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT / "Tools" / "athena_studio.py"
VERSION = ROOT / "Core" / "version.py"

REQUIRED_METHODS = {
    "_setup_style",
    "_status_card",
    "_button_group",
    "refresh_studio_ui",
    "reload_patched_build",
    "export_studio_log",
    "create_diagnostic_bundle",
}

REQUIRED_UI_MARKERS = [
    "Runtime Center",
    "Validation Center",
    "Doctor Center",
    "Intelligence Tools",
    "Logs & Diagnostics",
    "Athena Studio Beta Tile UI",
    "Hover over controls for help",
    "SimpleToolTip",
    "Studio.TButton",
    "Studio.Tile.TButton",
    "Success.TLabel",
]

REQUIRED_BUTTONS = [
    "▶ Launch",
    "🌐 Open Scout",
    "🔄 Reload",
    "🔃 Refresh",
    "✅ Validate Everything",
    "🩺 Doctor Everything",
    "📤 Export Studio Log",
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


def main() -> int:
    print("Athena Studio Beta UI Validation")
    print("=" * 60)
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
            failures.append("Missing Studio Beta UI methods: " + ", ".join(missing_methods))
        else:
            print(f"[PASS] required Beta UI methods present: {len(REQUIRED_METHODS)}")
        missing_markers = [marker for marker in REQUIRED_UI_MARKERS if marker not in text]
        if missing_markers:
            failures.append("Missing Beta UI markers: " + ", ".join(missing_markers))
        else:
            print(f"[PASS] required Beta UI markers present: {len(REQUIRED_UI_MARKERS)}")
        missing_buttons = [button for button in REQUIRED_BUTTONS if button not in text]
        if missing_buttons:
            failures.append("Missing Beta UI button labels: " + ", ".join(missing_buttons))
        else:
            print(f"[PASS] required Beta UI buttons present: {len(REQUIRED_BUTTONS)}")
    version = _version_value("ATHENA_VERSION")
    scout = _version_value("SCOUT_VERSION")
    build = _version_value("ATHENA_BUILD")
    if not (version.startswith("0.5.0-drop4e") or __import__("re").fullmatch(r"\d+\.\d+\.\d+\.\d+\.\d+", version)):
        failures.append(f"Unexpected ATHENA_VERSION: {version}")
    elif scout != "v" + version:
        failures.append(f"SCOUT_VERSION mismatch: {scout} vs {version}")
    elif not (build.startswith("drop4e") or __import__("re").fullmatch(r"\d+\.\d+\.\d+\.\d+\.\d+", build)):
        failures.append(f"Unexpected ATHENA_BUILD: {build}")
    else:
        print(f"[PASS] version metadata: {version} / {scout} / {build}")
    if failures:
        print("\nOverall status: FAIL")
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1
    print("\nOverall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
