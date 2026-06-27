"""Scout runtime doctor."""
from __future__ import annotations

from pathlib import Path
import socket
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

print("Scout Runtime Doctor")
print("====================")
print("Root:", ROOT)
print("Python:", sys.executable)

for rel in ["launch.py", "Scout/app.py", "Scout/run_scout.py", "Core/version.py"]:
    p = ROOT / rel
    print(f"{'PASS' if p.exists() else 'FAIL'} {rel}")

try:
    from Core.version import ATHENA_VERSION, SCOUT_VERSION
    print("PASS version import:", ATHENA_VERSION, SCOUT_VERSION)
except Exception as exc:
    print("FAIL version import:", exc)

try:
    import Scout.app as app
    print("PASS Scout.app import")
    print("Resolved version:", getattr(app, "SCOUT_VERSION", None))
except Exception as exc:
    print("FAIL Scout.app import:", exc)
    traceback.print_exc()

for port in range(8765, 8770):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        busy = sock.connect_ex(("localhost", port)) == 0
    print(f"Port {port}: {'BUSY' if busy else 'free'}")
