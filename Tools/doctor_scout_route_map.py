"""Doctor for Scout route-map and targeted-routing cleanup."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    print("Scout Route Map / Targeted Routing Doctor")
    print("=" * 60)
    required = [
        ROOT / "docs" / "SCOUT_ROUTE_MAP_v0.5.5.5.18.md",
        ROOT / "Scout" / "conversation" / "router.py",
        ROOT / "Knowledge" / "Intelligence" / "Routing" / "request_router.py",
        ROOT / "Knowledge" / "Intelligence" / "Public" / "public_answers.py",
        ROOT / "Tests" / "validate_scout_route_map_and_targeted_routing_v055518.py",
    ]
    failed = []
    for path in required:
        ok = path.exists()
        print(f"[{'PASS' if ok else 'FAIL'}] required file: {path.relative_to(ROOT)}")
        if not ok:
            failed.append(str(path.relative_to(ROOT)))
    if failed:
        print("Overall status: FAIL")
        return 1
    result = subprocess.run(
        [sys.executable, "-B", "Tests/validate_scout_route_map_and_targeted_routing_v055518.py"],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    print("Overall status:", "PASS" if result.returncode == 0 else "FAIL")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
