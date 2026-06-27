"""Doctor for Studio diagnostics log export workflow restoration."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

STUDIO = PROJECT_ROOT / "Tools" / "athena_studio.py"
VERSION = PROJECT_ROOT / "Core" / "version.py"


def report(name: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))
    return ok


def main() -> int:
    print("Diagnostics Log Export Workflow Doctor")
    print("=" * 60)
    checks: list[bool] = []
    checks.append(report("studio exists", STUDIO.exists(), str(STUDIO)))
    text = STUDIO.read_text(encoding="utf-8")
    tree = ast.parse(text)
    methods = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    checks.append(report("export_diagnostics_logs method", "export_diagnostics_logs" in methods))
    checks.append(report("open_reports method", "open_reports" in methods))
    checks.append(report("folder opener method", "_open_folder" in methods))
    checks.append(report("diagnostics export button", "📁 Export Diagnostics Logs" in text))
    checks.append(report("open reports button", "📂 Open Reports" in text))
    checks.append(report("timestamped folder export", "diagnostics_export_" in text and "export_dir.mkdir" in text))
    checks.append(report("copies scout debug exports", "scout_debug_export_*.txt" in text and "scout_debug_export_*.json" in text))
    checks.append(report("copies session logs", "scout_session_log.txt" in text and "scout_session_log.json" in text))
    checks.append(report("writes manifest", "diagnostics_manifest.json" in text))
    checks.append(report("opens export folder", "self._open_folder(export_dir)" in text))
    from Core.version import ATHENA_VERSION, ATHENA_BUILD, SCOUT_VERSION, RELEASE_NAME
    checks.append(report("version advanced", ATHENA_VERSION == ATHENA_BUILD and SCOUT_VERSION == "v" + ATHENA_VERSION and ATHENA_VERSION >= "0.5.5.5.15", f"{ATHENA_VERSION} / {RELEASE_NAME}"))
    failed = len([x for x in checks if not x])
    print("-" * 60)
    print(f"Passed: {len(checks)-failed}")
    print(f"Failed: {failed}")
    print("Overall status:", "PASS" if failed == 0 else "FAIL")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
