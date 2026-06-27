"""Athena Scout Launcher

Spyder-friendly launcher.

Run:
    %runfile F:/Development/Athena/Tools/launch_scout.py --wdir

Then open:
    http://localhost:8765/?cache_bust=1

This launcher:
- prints the exact app file being served
- prints the loaded Scout/Core versions
- verifies the placeholder-only question box patch is present
- warns if the port is already in use
- opens the browser automatically
"""
from __future__ import annotations

from pathlib import Path
import socket
import sys
import time
import webbrowser


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HOST = "localhost"
PORT = 8765
URL = f"http://{HOST}:{PORT}/?cache_bust={int(time.time())}"


def _ensure_project_root() -> None:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))


def _port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def _preflight() -> None:
    app_path = PROJECT_ROOT / "Scout" / "app.py"
    print("Athena Scout Launcher")
    print("=====================")
    print("Project root:", PROJECT_ROOT)
    print("Scout app   :", app_path)
    print("URL         :", URL)
    print()

    if not app_path.exists():
        raise RuntimeError(f"Scout app not found: {app_path}")

    text = app_path.read_text(encoding="utf-8")
    if ">Who are the most active managers?</textarea>" in text:
        print("[WARN] Old prefilled question text is still present in Scout/app.py")
    else:
        print("[PASS] Scout question box is placeholder-only")

    try:
        from Core.version import ATHENA_VERSION, SCOUT_VERSION
        print("[INFO] Athena version:", ATHENA_VERSION)
        print("[INFO] Scout version:", SCOUT_VERSION)
    except Exception as ex:
        print("[WARN] Could not read Core.version:", ex)

    if _port_in_use(HOST, PORT):
        print()
        print("[WARN] Port 8765 is already in use.")
        print("       A previous Scout server may still be running.")
        print("       Open the URL below. If it looks stale, stop the old server/kernel and relaunch.")
        print("       URL:", URL)
        webbrowser.open(URL)
        return

    print("[PASS] Port 8765 is free")
    print()


def main() -> None:
    _ensure_project_root()
    _preflight()

    if _port_in_use(HOST, PORT):
        return

    from Scout.app import serve

    print("Launching Scout...")
    print("Leave this console running while using Scout.")
    print("Press Ctrl+C to stop.")
    print()
    webbrowser.open(URL)
    serve(host=HOST, port=PORT)


if __name__ == "__main__":
    main()
