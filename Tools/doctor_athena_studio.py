"""Doctor checks for Athena Studio runtime assumptions."""
from __future__ import annotations

import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def is_port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def main() -> int:
    print("Athena Studio Doctor")
    print("=" * 28)
    failures: list[str] = []
    checks = [
        ("Core/version.py", ROOT / "Core" / "version.py"),
        ("Tools/athena_studio.py", ROOT / "Tools" / "athena_studio.py"),
        ("Athena Studio.bat", ROOT / "Athena Studio.bat"),
        ("Scout/app.py", ROOT / "Scout" / "app.py"),
    ]
    for label, path in checks:
        if path.exists():
            print(f"[PASS] {label}: {path}")
        else:
            print(f"[WARN] {label} missing: {path}")
            if label in {"Core/version.py", "Tools/athena_studio.py"}:
                failures.append(f"missing required {label}")
    nested = ROOT / "Athena"
    duplicate_runtime = (nested / "Core").exists() or (nested / "Scout").exists()
    if duplicate_runtime:
        failures.append("nested Athena runtime duplicate found")
        print(f"[FAIL] nested runtime duplicate: {nested}")
    else:
        print("[PASS] no nested Athena runtime duplicate detected")
    print(f"[INFO] Python: {sys.executable}")
    listening = [port for port in range(8765, 8795) if is_port_open(port)]
    print("[INFO] Scout-range ports listening: " + (", ".join(map(str, listening)) if listening else "none"))
    if failures:
        print("\nOverall status: FAIL")
        return 1
    print("\nOverall status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
