"""
Fetch Fantrax player statistics / production.

Fetch layer responsibility:
- Call provider client.
- Save raw provider payload only when a valid stats payload is returned.
- No normalization.
- No analysis.

The endpoint is configurable because Fantrax endpoint names can differ by sport/view.
If provider.endpoints.player_stats exists, it is attempted first. Otherwise this module
tries a conservative list of likely Fantrax stats endpoints and saves the first valid
non-error payload.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from Core.json_utils import write_json
from Core.logger import log, log_header, log_section
from Core.project_paths import LOGS_DIR
from Providers.Fantrax.fantrax_client import FantraxClient


OUTPUT_FILENAME = "player_stats.json"
DISCOVERY_LOG = LOGS_DIR / "fantrax_player_stats_discovery.json"

# Candidate endpoints are intentionally Fetch-only. No downstream module relies on
# which endpoint succeeds; downstream modules consume Raw/player_stats.json only.
CANDIDATE_ENDPOINTS = [
    "players/getPlayerStats",
    "players/getPlayerStatsForLeague",
    "players/getPlayerStatsByLeague",
    "players/getPlayerScores",
    "players/getPlayerScoresForLeague",
    "stats/getPlayerStats",
    "stats/getPlayerStatsForLeague",
    "stats/getStats",
    "playerStats/getPlayerStats",
]

PARAM_SETS = [
    {},
    {"season": None},
    {"statsType": "STANDARD"},
    {"statsType": "FANTASY"},
]


def _payload_size(payload: Any) -> int:
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        return len(payload)
    return 0


def _looks_non_empty(payload: Any) -> bool:
    if isinstance(payload, list):
        return len(payload) > 0
    if isinstance(payload, dict):
        if payload.get("error"):
            return False
        return len(payload) > 0
    return False


def _clean_params(client: FantraxClient, params: dict[str, Any]) -> dict[str, Any]:
    cleaned = {}
    for key, value in params.items():
        if value is None and key == "season" and client.season:
            cleaned[key] = client.season
        elif value is not None:
            cleaned[key] = value
    return cleaned


def _candidate_endpoints(client: FantraxClient) -> list[str]:
    configured = client.get_optional_endpoint("player_stats", "")
    endpoints = []
    if configured:
        endpoints.append(configured)
    for endpoint in CANDIDATE_ENDPOINTS:
        if endpoint not in endpoints:
            endpoints.append(endpoint)
    return endpoints


def main() -> None:
    log_header("FETCH FANTRAX PLAYER STATS")

    client = FantraxClient()
    attempts: list[dict[str, Any]] = []

    for endpoint in _candidate_endpoints(client):
        for params in PARAM_SETS:
            request_params = _clean_params(client, params)
            label = f"{endpoint} params={request_params}"
            log(f"Trying {label}")

            try:
                payload = client.get_player_stats(endpoint=endpoint, params=request_params)
                client.validate_payload(payload, label)
            except Exception as exc:  # fetch diagnostics only; continue discovery
                attempts.append(
                    {
                        "endpoint": endpoint,
                        "params": request_params,
                        "status": "failed",
                        "error": str(exc),
                    }
                )
                continue

            attempts.append(
                {
                    "endpoint": endpoint,
                    "params": request_params,
                    "status": "valid_response",
                    "payload_type": type(payload).__name__,
                    "payload_size": _payload_size(payload),
                }
            )

            if _looks_non_empty(payload):
                client.save_raw_json(OUTPUT_FILENAME, payload)
                write_json(DISCOVERY_LOG, attempts)
                log("")
                log_section("Successful Endpoint")
                log(f"Endpoint: {endpoint}")
                log(f"Params: {request_params}")
                log(f"Discovery log: {DISCOVERY_LOG}")
                log("Fetch complete.")
                return

    write_json(DISCOVERY_LOG, attempts)
    log("")
    log_section("No Valid Player Stats Payload Found")
    log(f"Discovery log: {DISCOVERY_LOG}")
    log("No Raw/player_stats.json file was overwritten.")
    raise RuntimeError(
        "Could not discover a valid Fantrax player stats endpoint. "
        "Review Logs/fantrax_player_stats_discovery.json and configure "
        "provider.endpoints.player_stats if needed."
    )


if __name__ == "__main__":
    main()
