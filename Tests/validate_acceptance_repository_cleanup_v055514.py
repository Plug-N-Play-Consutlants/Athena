"""Validate v0.5.5.5.14 acceptance repository cleanup.

This guard checks the cleanup/refactor state after the aligned .11/.12 patch:
canonical versioning, no malformed nested patch roots, root-level duplicate
Athena modules reduced to shims, public renderer diagnostics gated, and public
team analytical prompts avoiding the knowledge-gap path.
"""
from __future__ import annotations

from pathlib import Path
import ast
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.version import ATHENA_VERSION, SCOUT_VERSION, ATHENA_BUILD
from Scout.conversation.router import route_question

SHIM_FILES = [
    "connect.py", "orchestrator.py", "status.py", "sync.py",
    "workspace.py", "operation_result.py", "exceptions.py",
]

def check(name: str, condition: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if condition else 'FAIL'}] {name}: {detail}")
    return condition

def main() -> int:
    results = []
    results.append(check("version", ATHENA_VERSION == "0.5.5.5.14", ATHENA_VERSION))
    results.append(check("scout_version", SCOUT_VERSION == "v0.5.5.5.14", SCOUT_VERSION))
    results.append(check("build", ATHENA_BUILD == "0.5.5.5.14", ATHENA_BUILD))

    nested = ROOT / "AthenaEngine"
    results.append(check("no_nested_athenaengine_root", not nested.exists(), str(nested)))

    malformed_roots = [ROOT.parent / "Scout", ROOT.parent / "Knowledge", ROOT.parent / "Core"]
    results.append(check("no_malformed_patch_residue_roots", not any(p.exists() for p in malformed_roots), ", ".join(str(p) for p in malformed_roots if p.exists())))

    for rel in SHIM_FILES:
        text = (ROOT / rel).read_text(encoding="utf-8")
        results.append(check(f"root_shim_{rel}", "Canonical implementation lives" in text and "import *" in text, text.splitlines()[0] if text else ""))

    app_text = (ROOT / "Scout" / "app.py").read_text(encoding="utf-8")
    results.append(check("renderer_public_comment_first", "const publicText = String(answer.public_comment || '').trim();" in app_text))
    results.append(check("renderer_developer_gate", "const developerActive = isDeveloperModeActive();" in app_text and "if (developerActive)" in app_text))
    results.append(check("renderer_diagnostic_block_declared", "let diagnosticBlock = ''" in app_text))

    dallas = route_question("How good are the Dallas Stars?", mode="public")
    dallas_public = str(dallas.get("public_comment", ""))
    results.append(check("dallas_not_gap", dallas.get("intent") != "public_intelligence_gap", str(dallas.get("intent"))))
    results.append(check("dallas_analytical_depth", "Analytical lens:" in dallas_public and "Roster read:" in dallas_public, dallas_public[:160]))

    leafs = route_question("Tell me about the Toronto Maple Leafs", mode="public")
    leafs_public = str(leafs.get("public_comment", ""))
    results.append(check("team_profile_depth", "Analytical lens:" in leafs_public and "Roster read:" in leafs_public, leafs_public[:160]))

    parse_failures = []
    for path in ROOT.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"))
        except Exception as exc:
            parse_failures.append(f"{path.relative_to(ROOT)}: {exc}")
    results.append(check("python_syntax_scan", not parse_failures, "; ".join(parse_failures[:3])))

    ok = all(results)
    print("\nv0.5.5.5.14 acceptance repository cleanup validation:", "PASS" if ok else "FAIL")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
