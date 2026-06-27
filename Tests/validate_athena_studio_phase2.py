"""Validate Athena Studio Phase 2 dashboard/PIF observability."""
from __future__ import annotations

import ast
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT / "Tools" / "athena_studio.py"
VERSION = ROOT / "Core" / "version.py"

REQUIRED_METHODS = {
    "show_pif_coverage",
    "show_knowledge_dashboard",
    "show_provider_dashboard",
    "inspect_pif_prompt",
    "validate_everything",
    "doctor_everything",
    "create_diagnostic_bundle",
}
REQUIRED_LABELS = ["PIF Coverage", "Knowledge Dashboard", "Provider Dashboard", "Allowed domains", "Blocked domains"]


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
    print("Athena Studio Phase 2 Validation")
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
        missing = sorted(REQUIRED_METHODS - methods)
        if missing:
            failures.append("Missing Studio methods: " + ", ".join(missing))
        else:
            print(f"[PASS] required Phase 2 methods present: {len(REQUIRED_METHODS)}")
        missing_labels = [label for label in REQUIRED_LABELS if label not in text]
        if missing_labels:
            failures.append("Missing Studio labels: " + ", ".join(missing_labels))
        else:
            print(f"[PASS] required Phase 2 labels present: {len(REQUIRED_LABELS)}")
    version = _version_value("ATHENA_VERSION")
    build = _version_value("ATHENA_BUILD")
    scout_version = _version_value("SCOUT_VERSION")
    if not (version.startswith("0.5.0-drop4e") or __import__("re").fullmatch(r"\d+\.\d+\.\d+\.\d+\.\d+", version)):
        failures.append(f"Unexpected ATHENA_VERSION format: {version}")
    elif not (build.startswith("drop4e") or __import__("re").fullmatch(r"\d+\.\d+\.\d+\.\d+\.\d+", build)):
        failures.append(f"Unexpected ATHENA_BUILD format: {build}")
    elif scout_version != "v" + version:
        failures.append(f"SCOUT_VERSION does not match ATHENA_VERSION: {scout_version} vs {version}")
    else:
        print(f"[PASS] version metadata: {version} / {scout_version} / {build}")
    if failures:
        print("\nOverall status: FAIL")
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1
    print("\nOverall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
