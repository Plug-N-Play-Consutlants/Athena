"""Validate Athena Studio PIF inspector integration."""
from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    print("Athena Studio PIF Inspector Validation")
    print("=" * 52)
    studio_path = ROOT / "Tools" / "athena_studio.py"
    source = studio_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    methods = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    required = {"inspect_pif_prompt", "run_pif_suite", "validate_pif", "doctor_pif", "runtime_audit"}
    missing = sorted(required - methods)
    if missing:
        print("[FAIL] missing methods: " + ", ".join(missing))
        return 1
    print("[PASS] Studio PIF inspector methods present")

    from Knowledge.Intelligence.Routing.request_router import analyze_public_request
    checks = {
        "Austin Matthews": "player_intelligence",
        "Compare Matthews and McDavid": "player_comparison",
        "Who is Sebastian Aho?": "disambiguate_entity",
        "If the NHL draft were today, who goes first?": "draft_intelligence_gap",
    }
    failed = []
    for prompt, expected_route in checks.items():
        result = analyze_public_request(prompt)
        print(f"[CHECK] {prompt!r}: intent={result.intent.intent.value}; route={result.route}; confidence={result.confidence}")
        if result.route != expected_route:
            failed.append((prompt, expected_route, result.route))
    if failed:
        print("[FAIL] routing checks failed")
        for prompt, expected, actual in failed:
            print(f" - {prompt!r}: expected {expected}, got {actual}")
        return 1
    print("[PASS] PIF routing checks usable from Studio context")
    print("Overall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
