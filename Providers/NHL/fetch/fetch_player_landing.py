"""
Fetch NHL player landing payloads for players resolved through the identity map.

Fetch layer responsibility:
- Read canonical identity mapping only to know which NHL player IDs to request.
- Download raw NHL player landing payloads.
- Save raw provider payload.
- No fantasy league logic.
- No canonical normalization.

Output:
    Raw/nhl_player_landing.json
"""

from __future__ import annotations

from pathlib import Path
import sys
import time
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.json_utils import read_json, write_json
from Core.logger import log, log_header, log_section
from Core.project_paths import OUTPUT_DIR, RAW_DIR
from Providers.NHL.nhl_client import NHLClient

IDENTITY_MAP_PATH = OUTPUT_DIR / "player_identity_map.json"
OUTPUT_PATH = RAW_DIR / "nhl_player_landing.json"

REQUEST_DELAY_SECONDS = 0.05


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _resolved_nhl_player_ids(identity_rows: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()

    for row in identity_rows:
        if not isinstance(row, dict):
            continue
        status = _safe_str(row.get("resolution_status")).lower()
        if status not in {"resolved", "review"}:
            continue
        player_id = _safe_str(row.get("nhl_player_id"))
        if not player_id or player_id in seen:
            continue
        seen.add(player_id)
        ids.append(player_id)

    return ids


def fetch_player_landing() -> dict[str, Any]:
    log_header("FETCH NHL PLAYER LANDING")

    identity_rows = read_json(IDENTITY_MAP_PATH)
    if not isinstance(identity_rows, list):
        raise ValueError("player_identity_map.json must contain a list of identity records.")

    player_ids = _resolved_nhl_player_ids(identity_rows)
    client = NHLClient()

    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    log(f"Identity Rows: {len(identity_rows)}")
    log(f"NHL Player IDs To Fetch: {len(player_ids)}")

    for index, player_id in enumerate(player_ids, start=1):
        try:
            payload = client.get_player_landing(player_id)
            records.append(
                {
                    "nhl_player_id": player_id,
                    "payload": payload,
                }
            )
        except Exception as exc:
            errors.append(
                {
                    "nhl_player_id": player_id,
                    "error": str(exc),
                }
            )

        if index % 25 == 0 or index == len(player_ids):
            log(f"Fetched {index}/{len(player_ids)} player landing payloads")

        if REQUEST_DELAY_SECONDS:
            time.sleep(REQUEST_DELAY_SECONDS)

    output = {
        "summary": {
            "identity_rows": len(identity_rows),
            "requested_players": len(player_ids),
            "fetched_players": len(records),
            "errors": len(errors),
            "source": "nhl_player_landing",
        },
        "players": records,
        "errors": errors,
    }

    write_json(OUTPUT_PATH, output)

    log_section("Fetch Summary")
    log(f"Fetched: {len(records)}")
    log(f"Errors: {len(errors)}")
    log(f"Output: {OUTPUT_PATH}")
    log("Completed successfully.")

    return output


if __name__ == "__main__":
    fetch_player_landing()
