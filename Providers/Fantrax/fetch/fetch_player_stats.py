"""Fetch raw player statistics using the single authenticated fxpa provider contract.

Raw response is evidence of a provider reply, NOT verified period G+A.
Athena/Investigation owns temporal and semantic verification.
"""
from __future__ import annotations
from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from Providers.Fantrax.fantrax_client import FantraxClient
from Core.logger import log, log_header


def main() -> None:
    log_header("FETCH FANTRAX PLAYER STATS")
    client = FantraxClient()
    if not client.has_cookie_auth():
        raise PermissionError("Authenticated Fantrax session required")
    payload = client.get_player_stats()
    if client.is_error_payload(payload):
        raise RuntimeError("Fantrax fxpa getPlayerStats rejected the request")
    if not isinstance(payload, dict):
        raise ValueError("Unexpected Fantrax fxpa getPlayerStats payload")
    # Do not overwrite canonical production artifacts with unverified totals.
    client.save_raw_json("player_stats_fxpa_unverified.json", payload)
    log("Saved raw unverified player statistics; period validation remains required")


if __name__ == "__main__":
    main()
