"""Validate Athena Studio tile-style command dashboard."""
from __future__ import annotations

import ast
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT / "Tools" / "athena_studio.py"
VERSION = ROOT / "Core" / "version.py"

REQUIRED_METHODS = {"_tile_text", "_tile_columns", "_button_group", "_status_card", "refresh_studio_ui", "reload_patched_build"}
REQUIRED_MARKERS = [
    "Studio.Tile.TButton",
    "compact two-line dashboard tile label",
    "compact dashboard tile grid",
    "Compact tiles use icons",
    "Athena Studio Compact Tile UI",
]
REQUIRED_ACTIONS = [
    "▶ Launch",
    "🔄 Reload",
    "🧹 Clean Runtime",
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
    print("Athena Studio Tile UI Validation")
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
            failures.append("Missing Tile UI methods: " + ", ".join(missing_methods))
        else:
            print(f"[PASS] required Tile UI methods present: {len(REQUIRED_METHODS)}")
        missing_markers = [m for m in REQUIRED_MARKERS if m not in text]
        if missing_markers:
            failures.append("Missing Tile UI markers: " + ", ".join(missing_markers))
        else:
            print(f"[PASS] required Tile UI markers present: {len(REQUIRED_MARKERS)}")
        missing_actions = [a for a in REQUIRED_ACTIONS if a not in text]
        if missing_actions:
            failures.append("Missing action labels: " + ", ".join(missing_actions))
        else:
            print(f"[PASS] required action labels present: {len(REQUIRED_ACTIONS)}")
    version = _version_value("ATHENA_VERSION")
    scout = _version_value("SCOUT_VERSION")
    build = _version_value("ATHENA_BUILD")
    if not (version in {"0.5.0-drop4e38", "0.5.0-drop4e39", "0.5.0-drop4e40"} or __import__("re").fullmatch(r"\d+\.\d+\.\d+\.\d+\.\d+", version)):
        failures.append(f"Unexpected ATHENA_VERSION: {version}")
    elif scout != "v" + version:
        failures.append(f"SCOUT_VERSION mismatch: {scout} vs {version}")
    elif not (build in {"drop4e38", "drop4e39", "drop4e40"} or __import__("re").fullmatch(r"\d+\.\d+\.\d+\.\d+\.\d+", build)):
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
