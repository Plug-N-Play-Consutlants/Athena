"""Fetch authenticated Fantrax current and future draft-pick ownership."""
from __future__ import annotations
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.logger import log, log_header
from Providers.Fantrax.fantrax_client import FantraxClient

OUTPUT_FILENAME = "draft_picks.json"


def fetch_draft_picks() -> Any:
    client = FantraxClient()
    payload = client.get_draft_picks()
    client.validate_payload(payload, "Fantrax draft picks")
    client.save_raw_json(OUTPUT_FILENAME, payload)
    if isinstance(payload, dict):
        log(f"Current draft picks returned: {len(payload.get('currentDraftPicks') or [])}")
        log(f"Future draft picks returned: {len(payload.get('futureDraftPicks') or [])}")
    return payload


def main() -> None:
    log_header("FETCH FANTRAX DRAFT PICKS")
    fetch_draft_picks()
    log("")
    log("Fetch complete.")


if __name__ == "__main__":
    main()
