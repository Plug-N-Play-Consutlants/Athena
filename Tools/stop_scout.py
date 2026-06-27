"""Stop stale Scout server processes.

Spyder:
    %runfile F:/Development/Athena/Tools/stop_scout.py --wdir

Default is dry-run. To actually kill the process, set APPLY = True below.
"""

from __future__ import annotations

import re
import subprocess


PORT = 8765
APPLY = True  # change to True to kill process using PORT


def _netstat_lines(port: int):
    cmd = ["netstat", "-ano"]
    result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or "netstat failed")
    needle = f":{port}"
    return [line for line in result.stdout.splitlines() if needle in line and "LISTENING" in line]


def _pids_from_lines(lines):
    pids = set()
    for line in lines:
        parts = line.split()
        if parts and parts[-1].isdigit():
            pids.add(parts[-1])
    return sorted(pids)


def main():
    print("Scout Stopper")
    print("=============")
    print("Port:", PORT)
    print("Mode:", "APPLY" if APPLY else "DRY RUN")
    print()

    lines = _netstat_lines(PORT)
    if not lines:
        print("[PASS] No process is listening on port", PORT)
        return

    print("[WARN] Process found on Scout port:")
    for line in lines:
        print(" ", line)

    pids = _pids_from_lines(lines)
    print()
    print("PIDs:", ", ".join(pids) if pids else "none detected")

    if not APPLY:
        print()
        print("Dry run only. To stop Scout, set APPLY = True and rerun.")
        return

    for pid in pids:
        print("Killing PID", pid)
        subprocess.run(["taskkill", "/PID", pid, "/F"], shell=False)

    print()
    print("Done. Rerun launch_scout_fresh.py.")


if __name__ == "__main__":
    main()
