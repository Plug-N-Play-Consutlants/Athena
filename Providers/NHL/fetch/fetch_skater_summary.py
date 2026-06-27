"""
Fetch NHL skater season summary statistics.

Fetch layer responsibility:
- Download public NHL player production data.
- Save raw provider payload.
- No normalization.
- No fantasy league logic.

Output:
    Raw/nhl_skater_summary.json
"""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.config import get_workspace_value
from Core.logger import log, log_header, log_section
from Providers.NHL.nhl_client import NHLClient

OUTPUT_FILENAME = "nhl_skater_summary.json"


def _workspace_season_to_nhl_season_id(value: str) -> str:
    """
    Convert workspace season to NHL seasonId.

    Examples:
        "2025" -> "20252026"
        "20252026" -> "20252026"
    """
    season = str(value or "").strip()
    if len(season) == 8 and season.isdigit():
        return season
    if len(season) == 4 and season.isdigit():
        start = int(season)
        return f"{start}{start + 1}"
    raise ValueError(
        "Unable to derive NHL season id. Set workspace.season to YYYY or YYYYYYYY."
    )


def main() -> None:
    log_header("FETCH NHL SKATER SUMMARY")

    workspace_season = get_workspace_value("workspace.season", "")
    season_id = _workspace_season_to_nhl_season_id(workspace_season)

    log(f"Workspace Season: {workspace_season}")
    log(f"NHL Season ID: {season_id}")
    log("Game Type: 2 regular season")

    client = NHLClient()
    payload = client.get_skater_summary(season_id=season_id, game_type_id=2, limit=-1)
    client.save_raw_json(OUTPUT_FILENAME, payload)

    row_count = 0
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            row_count = len(data)
    elif isinstance(payload, list):
        row_count = len(payload)

    log_section("Fetch Summary")
    log(f"Rows: {row_count}")
    log(f"Output: Raw/{OUTPUT_FILENAME}")
    log("Completed successfully.")


if __name__ == "__main__":
    main()
