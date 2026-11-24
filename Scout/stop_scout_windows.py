"""Safely stop only Scout servers verified as belonging to this repository.

An unrelated HTTP server, or Scout running from a different repository root,
will NEVER be terminated by Studio's reload/stop action.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request

PORT_RANGE = range(8765, 8795)
ROOT = Path(__file__).resolve().parents[1]


def _parse_netstat_listeners(output: str) -> dict[int, set[str]]:
    """Parse Windows netstat regardless of TCP v4/v6 or localised state text.

    Only the LOCAL endpoint and a numeric PID are used; remote connections
    must never be considered listening Scout processes.
    """
    found: dict[int, set[str]] = {}
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0].upper() != "TCP":
            continue
        local, state, pid = parts[1], parts[-2], parts[-1]
        # Windows emits LISTENING for both address families (possibly translated
        # on localised systems); omit ESTABLISHED/CLOSE_WAIT/etc explicitly.
        if not pid.isdecimal() or (state.upper() not in {"LISTENING", "ABHÖREN", "ESCUCHANDO"}):
            continue
        try:
            port = int(local.rsplit(":", 1)[1])
        except (IndexError, ValueError):
            continue
        if port in PORT_RANGE:
            found.setdefault(port, set()).add(pid)
    return found


def find_listening_pids() -> dict[int, set[str]]:
    # Do not use '-p tcp': on Windows it can omit TCPv6 listeners. Enumerate both.
    result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
    found = _parse_netstat_listeners(result.stdout)
    if found:
        return found
    # PowerShell is an independent source when netstat output is restricted,
    # localised, or unavailable. Never infer a PID from a bare HTTP response.
    command = (
        "Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | "
        "Where-Object { $_.LocalPort -ge 8765 -and $_.LocalPort -le 8794 } | "
        "ForEach-Object { '{0},{1}' -f $_.LocalPort,$_.OwningProcess }"
    )
    try:
        ps = subprocess.run(["powershell", "-NoProfile", "-Command", command],
                            capture_output=True, text=True, timeout=8)
        for line in ps.stdout.splitlines():
            try:
                port, pid = (item.strip() for item in line.split(",", 1))
                if int(port) in PORT_RANGE and pid.isdecimal():
                    found.setdefault(int(port), set()).add(pid)
            except (ValueError, TypeError):
                continue
    except (OSError, subprocess.TimeoutExpired):
        pass
    return found


def is_our_scout(port: int) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/version", timeout=1.25) as response:
            data = json.load(response)
        if not isinstance(data, dict) or data.get("app") != "Scout":
            return False, "Listener is not an identified Scout server"
        provenance = data.get("runtime_provenance") or {}
        actual_root = provenance.get("project_root") or data.get("project_root") or ""
        same_root = os.path.normcase(os.path.abspath(str(actual_root))) == os.path.normcase(str(ROOT.resolve()))
        if not same_root:
            return False, f"Scout belongs to another repository: {actual_root}"
        return True, f"Scout {data.get('version', 'unknown')} at {actual_root}"
    except Exception as exc:
        return False, f"Unable to verify listener identity: {exc}"


def is_scout_process(pid: str, ports: set[int] | None = None) -> tuple[bool, str]:
    """Validate both the OS process and the serving Scout runtime.

    Older Studio launches use `python -B launch.py` with cwd=ROOT. Windows CIM
    does not include cwd in CommandLine, so checking only for ROOT produces
    false refusals. For this legacy case require matching process PID, Python
    executable, repository root, and a known Scout entrypoint from the live
    port's own /api/version endpoint. Never kill based on a port alone.
    """
    if not pid.isdecimal() or int(pid) <= 4:
        return False, "Unsafe or invalid process identifier"
    ps = ("$p = Get-CimInstance Win32_Process -Filter 'ProcessId = " + pid + "'; "
          "if ($p) { $p.ExecutablePath; $p.CommandLine }")
    try:
        result = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                                capture_output=True, text=True, timeout=8)
        lines = [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
        if result.returncode != 0 or len(lines) < 2:
            return False, "Process command line is unavailable or incomplete"
        executable = lines[0]
        command_line = " ".join(lines[1:])
        normalized = command_line.casefold().replace("/", "\\")
        project = str(ROOT.resolve()).casefold().replace("/", "\\")
        if "python" not in Path(executable).name.casefold():
            return False, "Listener PID is not a Python process"
        if project in normalized:
            return True, "Verified Athena-owned process (absolute command path)"

        # Legacy relative launches are accepted only when the HTTP identity
        # matches this very PID AND its Python executable, and the command
        # names one of Athena's actual launcher scripts.
        entrypoints = ("launch.py", "scout\\run_scout.py", "scout\\app.py",
                       "tools\\launch_scout.py")
        import re
        args = re.findall(r'"[^"]+"|\S+', command_line.casefold().replace("/", "\\"))
        script_args = [arg.strip('"') for arg in args[1:]]
        known_launcher = any(arg in entrypoints for arg in script_args)
        if not known_launcher:
            return False, "Process command line does not establish Athena repository ownership"
        if not ports:
            return False, "Relative launcher requires verified listener provenance"
        for port in sorted(ports):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/version", timeout=1.25) as response:
                    data = json.load(response)
                provenance = data.get("runtime_provenance") or {}
                claimed_root = provenance.get("project_root") or data.get("project_root")
                claimed_pid = provenance.get("process_id")
                claimed_python = provenance.get("python_executable")
                same_root = os.path.normcase(os.path.abspath(str(claimed_root or ""))) == os.path.normcase(str(ROOT.resolve()))
                same_executable = os.path.normcase(os.path.abspath(str(claimed_python or ""))) == os.path.normcase(os.path.abspath(executable))
                if data.get("app") != "Scout" or not same_root or claimed_pid != int(pid) or not same_executable:
                    return False, f"Port {port} runtime PID, root or executable mismatch"
            except Exception as exc:
                return False, f"Cannot verify relative-launch provenance on port {port}: {exc}"
        return True, "Verified Athena-owned legacy relative-launch process (PID/root/executable matched)"
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"Cannot verify process identity: {exc}"


def main() -> int:
    if os.name != "nt":
        print("Windows-only Scout stopping helper; no processes terminated.")
        return 0
    found = find_listening_pids()
    if not found:
        # Never claim success if Scout answers HTTP but process discovery failed.
        reachable = []
        for port in PORT_RANGE:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/version", timeout=0.18) as response:
                    data = json.load(response)
                if isinstance(data, dict) and data.get("app") == "Scout":
                    reachable.append(port)
            except Exception:
                continue
        if reachable:
            print(f"BLOCKED: Scout responds on port(s) {reachable} but Windows process discovery returned no PID. "
                  "Cannot safely terminate an unidentified listener.")
            return 2
        print("No Scout-range listening processes found.")
        return 0
    candidates = {}
    rejected = []
    for port, pids in found.items():
        accepted, reason = is_our_scout(port)
        print(f"Port {port}: {reason}; PID(s): {', '.join(sorted(pids))}")
        if not accepted:
            rejected.append((port, reason))
        else:
            for pid in pids:
                candidates.setdefault(pid, set()).add(port)
    if rejected:
        print("REFUSED: at least one Scout-range listener is unrelated or unverified; leaving it untouched.")
    if candidates and "--yes" not in sys.argv:
        if input("Terminate verified Scout processes? Type YES: ").strip() != "YES":
            return 1
    failed = False
    for pid, ports in candidates.items():
        # Re-verify every port immediately before stopping the associated PID.
        if not all(is_our_scout(port)[0] for port in ports):
            print(f"REFUSED PID {pid}: listener identity changed")
            failed = True
            continue
        process_ok, process_reason = is_scout_process(pid, ports)
        if not process_ok:
            print(f"REFUSED PID {pid}: {process_reason}")
            failed = True
            continue
        result = subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True, text=True)
        print((result.stdout or result.stderr).strip())
        failed = failed or result.returncode != 0
    return 1 if failed or rejected else 0


if __name__ == "__main__":
    raise SystemExit(main())
