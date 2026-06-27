"""
Scout local foreground launcher.

Run this file from Spyder/Anaconda with:

    runfile('F:/Development/Athena/launch.py',
            wdir='F:/Development/Athena')

This launcher intentionally runs Scout in the foreground so Spyder can stop it
cleanly and so server errors are visible in the console.
"""

from __future__ import annotations

import os
from pathlib import Path
import socket
import sys
import threading
import time
import urllib.request
import webbrowser

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCOUT_APP = PROJECT_ROOT / "Scout" / "app.py"
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8765
from Core.version import ATHENA_VERSION, SCOUT_VERSION


def _port_is_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((DEFAULT_HOST, port)) == 0


def _get_existing_version(port: int) -> str:
    try:
        with urllib.request.urlopen(f"http://{DEFAULT_HOST}:{port}/api/version", timeout=0.75) as response:
            return response.read().decode("utf-8", errors="replace")
    except Exception:
        return "unknown application or stale process"


def _choose_port(start: int = DEFAULT_PORT) -> int:
    strict = os.environ.get("SCOUT_STRICT_PORT") == "1"
    if strict:
        if not _port_is_open(start):
            return start
        existing = _get_existing_version(start)
        raise RuntimeError(f"Strict Scout port mode requires port {start}, but it is already in use by: {existing}")
    for port in range(start, start + 30):
        if not _port_is_open(port):
            return port
        print(f"Port {port} is already in use. Existing server: {_get_existing_version(port)}")
    raise RuntimeError("No available Scout port found between 8765 and 8794.")


def _print_header(port: int) -> None:
    print("SCOUT LOCAL LAUNCHER")
    print("=" * 60)
    print(f"Version:      {SCOUT_VERSION}")
    print(f"Athena:       {ATHENA_VERSION}")
    print(f"Mode:         foreground")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Scout app:    {SCOUT_APP}")
    print(f"Python:       {sys.executable}")
    print(f"URL:          http://{DEFAULT_HOST}:{port}")
    print("")


def launch_scout(open_browser: bool = True) -> int:
    """Launch Scout in the foreground and open a browser tab."""
    if os.environ.get("ATHENA_STUDIO_MANAGED") == "1":
        open_browser = False
    if not SCOUT_APP.exists():
        _print_header(DEFAULT_PORT)
        print("ERROR: Scout/app.py was not found.")
        return 1
    if PROJECT_ROOT.name.lower() != "athena":
        print(f"WARNING: Project root folder is named {PROJECT_ROOT.name!r}; expected Athena.")

    port = _choose_port(DEFAULT_PORT)
    _print_header(port)

    os.environ["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + os.environ.get("PYTHONPATH", "")
    os.environ["SCOUT_HOST"] = DEFAULT_HOST
    os.environ["SCOUT_PORT"] = str(port)
    os.environ["SCOUT_VERSION"] = SCOUT_VERSION

    # Spyder keeps modules alive between runfile calls. Force the app module to
    # be imported with the selected SCOUT_PORT and SCOUT_VERSION.
    for module_name in ["Scout.app"]:
        if module_name in sys.modules:
            del sys.modules[module_name]

    url = f"http://{DEFAULT_HOST}:{port}/?v={int(time.time())}"

    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    print("Launching Scout in foreground mode.")
    print("Keep this Spyder console running while using Scout.")
    print("Stop it with the red stop button / interrupt when finished.")
    print(f"Opening: {url}")
    print("")

    from Scout.app import serve

    serve(host=DEFAULT_HOST, port=port)
    return 0


if __name__ == "__main__":
    launch_scout()
