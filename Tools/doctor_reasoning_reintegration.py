"""Doctor for drop4e37 public reasoning reintegration."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MODULES = [
    "Knowledge.Intelligence.Public.public_answers",
    "Intelligence.Player.player_intelligence",
    "Reasoning.adapters.player_evidence_adapter",
    "Reasoning.reasoning_engine",
    "Reasoning.composition.executive_brief",
    "Scout.conversation.router",
]


def main() -> int:
    print("Reasoning Reintegration Doctor")
    print("=" * 60)
    failures = 0
    for name in MODULES:
        try:
            mod = importlib.import_module(name)
            print(f"[PASS] import: {name} -> {Path(mod.__file__).relative_to(ROOT)}")
        except Exception as ex:
            failures += 1
            print(f"[FAIL] import: {name}: {ex}")
    try:
        from Scout.conversation.router import route_question
        ans = route_question("Auston Matthews", mode="public")
        intel = (ans.get("developer") or {}).get("intelligence_used") or []
        if "reasoning_reintegration" in intel:
            print("[PASS] public player profile invokes reasoning_reintegration")
        else:
            failures += 1
            print(f"[FAIL] reasoning_reintegration missing: {intel}")
    except Exception as ex:
        failures += 1
        print(f"[FAIL] route smoke test: {ex}")
    print()
    if failures:
        print(f"Overall status: FAIL | failures={failures}")
        return 1
    print("Overall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
