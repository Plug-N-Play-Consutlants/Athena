"""
Optional Windows helper for inspecting or stopping stale Scout local servers.

Run from Spyder:

    runfile('F:/Development/Sports_Intelligence_Engine_2.0/Scout/stop_scout_windows.py',
            wdir='F:/Development/Sports_Intelligence_Engine_2.0')

This only targets processes listening on ports 8765-8794.
"""

from __future__ import annotations

import subprocess
import sys


PORT_RANGE = range(8765, 8795)


def _netstat_lines() -> list[str]:
    result = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True, shell=False)
    return result.stdout.splitlines()


def find_listening_pids() -> dict[int, set[str]]:
    found: dict[int, set[str]] = {}
    for line in _netstat_lines():
        if "LISTENING" not in line.upper():
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        local_address = parts[1]
        pid = parts[-1]
        for port in PORT_RANGE:
            if local_address.endswith(f":{port}"):
                found.setdefault(port, set()).add(pid)
    return found


def main() -> None:
    found = find_listening_pids()
    if not found:
        print("No Scout-range listening processes found on ports 8765-8794.")
        return

    print("Listening processes found:")
    for port, pids in found.items():
        print(f"  Port {port}: PID(s) {', '.join(sorted(pids))}")

    if "--yes" in sys.argv:
        answer = "YES"
    else:
        answer = input("Kill these processes? Type YES to continue: ").strip()
    if answer != "YES":
        print("No processes killed.")
        return

    killed = set()
    for pids in found.values():
        for pid in pids:
            if pid in killed:
                continue
            subprocess.run(["taskkill", "/PID", pid, "/F"], shell=False)
            killed.add(pid)
    print("Done.")


if __name__ == "__main__":
    main()
