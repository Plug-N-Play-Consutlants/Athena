"""Fresh Scout launcher.

This avoids stale localhost confusion by selecting a free port automatically.

Spyder:
    %runfile F:/Development/Athena/Tools/launch_scout_fresh.py --wdir

Then use the exact URL printed/opened by the launcher.
"""

from __future__ import annotations

from pathlib import Path
import socket
import sys
import time
import webbrowser


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HOST = "localhost"
PREFERRED_PORTS = [8765, 8766, 8767, 8768]


def _ensure_root():
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex((HOST, port)) == 0


def _choose_port() -> int:
    for port in PREFERRED_PORTS:
        if not _port_in_use(port):
            return port
    raise RuntimeError(f"No free Scout ports found in {PREFERRED_PORTS}")


def _version_string() -> str:
    try:
        import Core.version as version
        for attr in ("CURRENT_VERSION", "ATHENA_VERSION", "__version__", "VERSION"):
            value = getattr(version, attr, None)
            if value:
                return str(value)
        if hasattr(version, "get_version"):
            return str(version.get_version())
        return "Core.version loaded; no standard version attribute found"
    except Exception as ex:
        return f"unavailable ({ex})"


def main():
    _ensure_root()

    app_path = PROJECT_ROOT / "Scout" / "app.py"
    print("Fresh Scout Launcher")
    print("====================")
    print("Project root:", PROJECT_ROOT)
    print("Scout app   :", app_path)
    print("Version     :", _version_string())

    if not app_path.exists():
        raise RuntimeError(f"Scout app not found: {app_path}")

    text = app_path.read_text(encoding="utf-8")
    if ">Who are the most active managers?</textarea>" in text:
        print("[FAIL] Old prefilled question still exists in Scout/app.py")
        raise RuntimeError("Scout UI patch not present.")
    print("[PASS] Question box is placeholder-only")

    busy = [p for p in PREFERRED_PORTS if _port_in_use(p)]
    if busy:
        print("[INFO] Busy ports:", busy)

    port = _choose_port()
    url = f"http://{HOST}:{port}/?fresh={int(time.time())}"
    print("[PASS] Selected port:", port)
    print("URL:", url)
    print()
    print("Launching Scout. Leave this console running.")
    print("Press Ctrl+C to stop this Scout instance.")
    print()

    from Scout.app import serve

    webbrowser.open(url)
    serve(host=HOST, port=port)


if __name__ == "__main__":
    main()
