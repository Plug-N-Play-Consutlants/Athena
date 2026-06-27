"""Doctor for Athena credential persistence.

This reports safe metadata only. It never prints stored credential values.
"""
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main():
    print("Athena Credential Persistence Doctor")
    print("====================================")

    from Core.credential_store import credential_status, persistent_secrets_file

    status = credential_status()
    store = persistent_secrets_file()

    checks = [
        ("Persistent external store enabled", status.get("persistent_external_store") is True),
        ("Credential status exposes store path", bool(status.get("secrets_file"))),
        ("Store path is outside repo Configuration", "Configuration" not in str(store)),
        ("League secret status available", "fantrax_league_secret_present" in status),
        ("Cookie status available", "fantrax_cookie_parseable" in status),
    ]

    for label, ok in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}")

    print()
    print("Safe status")
    print("-----------")
    print("Secrets file exists:", bool(status.get("secrets_file_exists")))
    print("Secrets file:", status.get("secrets_file"))
    print("Repo migration source:", status.get("repo_secrets_file"))
    print("League secret present:", bool(status.get("fantrax_league_secret_present")))
    print("League secret saved at:", status.get("fantrax_league_secret_saved_at"))
    print("Browser cookie present:", bool(status.get("fantrax_cookie_present")))
    print("Browser cookie parseable:", bool(status.get("fantrax_cookie_parseable")))
    print("Browser cookie count:", int(status.get("fantrax_cookie_count") or 0))
    print("Browser cookie saved at:", status.get("fantrax_cookie_saved_at"))
    if status.get("last_rejected_secret_reason"):
        print("Last rejected auth reason:", status.get("last_rejected_secret_reason"))

    if not all(ok for _, ok in checks):
        raise RuntimeError("Credential persistence doctor failed.")

    print()
    print("STATUS: PASS")


if __name__ == "__main__":
    main()
