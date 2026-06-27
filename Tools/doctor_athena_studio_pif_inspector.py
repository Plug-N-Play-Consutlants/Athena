"""Doctor for Athena Studio PIF inspector wiring."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    print("Athena Studio PIF Inspector Doctor")
    print("=" * 52)
    checks = []
    files = [
        ROOT / "Tools" / "athena_studio.py",
        ROOT / "Knowledge" / "Intelligence" / "Routing" / "request_router.py",
        ROOT / "Knowledge" / "Intelligence" / "Intent" / "intent_classifier.py",
        ROOT / "Knowledge" / "Intelligence" / "Entities" / "entity_registry.py",
        ROOT / "Tests" / "validate_pif1_build001.py",
    ]
    for file in files:
        ok = file.exists()
        checks.append(ok)
        print(f"[{'PASS' if ok else 'FAIL'}] exists: {file.relative_to(ROOT)}")

    try:
        from Core.version import ATHENA_VERSION, SCOUT_VERSION
        print(f"[PASS] version import: Athena={ATHENA_VERSION}; Scout={SCOUT_VERSION}")
        checks.append(True)
    except Exception as exc:
        print(f"[FAIL] version import: {exc}")
        checks.append(False)

    try:
        from Knowledge.Intelligence.Routing.request_router import analyze_public_request
        samples = ["Auston Matthews", "Who is Sebastian Aho?", "Biggest trades this week"]
        for sample in samples:
            result = analyze_public_request(sample)
            print(f"[PASS] route sample: {sample!r} -> {result.intent.intent.value}/{result.route}")
        checks.append(True)
    except Exception as exc:
        print(f"[FAIL] PIF router import/use: {exc}")
        checks.append(False)

    if all(checks):
        print("Overall status: PASS")
        return 0
    print("Overall status: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
