"""
Fantrax Provider Capability Discovery.

Fetch-layer diagnostic utility.

Purpose:
- Probe likely Fantrax endpoints for the active workspace.
- Record which provider capabilities are available.
- Never overwrite canonical Raw snapshots.
- Help configure provider.endpoints.* once a valid endpoint is found.

This module performs no normalization and no analysis.
"""

from __future__ import annotations

from datetime import datetime, timezone
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

DISCOVERY_LOG = LOGS_DIR / "fantrax_provider_capabilities.json"

CAPABILITY_CANDIDATES: dict[str, list[str]] = {
    "league": [
        "general/getLeagueInfo",
    ],
    "players": [
        "players/getPlayerIds",
        "player/getPlayerIds",
        "players/getPlayers",
        "player/getPlayers",
        "league/getPlayerIds",
    ],
    "rosters": [
        "team/getTeamRosters",
        "teams/getTeamRosters",
        "roster/getTeamRosters",
        "rosters/getTeamRosters",
        "league/getTeamRosters",
        "team/getRosters",
        "rosters/getRosters",
        "roster/getRosters",
    ],
    "draft_picks": [
        "draft/getFutureDraftPicks",
        "draft/getDraftPicks",
        "draftPicks/getFutureDraftPicks",
        "league/getFutureDraftPicks",
        "league/getDraftPicks",
    ],
    "draft_results": [
        "draft/getDraftResults",
        "draft/getResults",
        "league/getDraftResults",
    ],
    "transactions": [
        "transactions/getTransactions",
        "transaction/getTransactions",
        "league/getTransactions",
        "transactions/getTransactionLog",
        "transaction/getTransactionLog",
    ],
    "schedule": [
        "schedule/getSchedule",
        "league/getSchedule",
        "matchups/getSchedule",
        "matchup/getSchedule",
    ],
    "player_stats": [
        "players/getPlayerStats",
        "players/getPlayerStatsForLeague",
        "players/getPlayerScores",
        "players/getPlayerScoresForLeague",
        "stats/getPlayerStats",
        "stats/getPlayerStatsForLeague",
        "stats/getStats",
        "playerStats/getPlayerStats",
    ],
}

PARAM_VARIANTS: list[dict[str, Any]] = [
    {},
    {"season": None},
    {"seasonId": None},
    {"statsType": "STANDARD"},
    {"statsType": "FANTASY"},
]


def _clean_params(client: FantraxClient, params: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in params.items():
        if value is None:
            if key in {"season", "seasonId"} and client.season:
                cleaned[key] = client.season
        else:
            cleaned[key] = value
    return cleaned


def _summarize_payload(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        if payload.get("error"):
            error = payload.get("error") or {}
            return {
                "valid": False,
                "kind": "error",
                "keys": list(payload.keys()),
                "error_code": error.get("code") if isinstance(error, dict) else None,
                "error_message": error.get("message") if isinstance(error, dict) else str(error),
                "size": 0,
            }
        return {
            "valid": len(payload) > 0,
            "kind": "dict",
            "keys": list(payload.keys())[:25],
            "size": len(payload),
        }
    if isinstance(payload, list):
        return {
            "valid": len(payload) > 0,
            "kind": "list",
            "keys": list(payload[0].keys())[:25] if payload and isinstance(payload[0], dict) else [],
            "size": len(payload),
        }
    return {
        "valid": False,
        "kind": type(payload).__name__,
        "keys": [],
        "size": 0,
    }


def discover_capability(client: FantraxClient, capability: str, endpoints: list[str]) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    first_valid: dict[str, Any] | None = None

    log_section(f"Capability: {capability}")

    for endpoint in endpoints:
        for params in PARAM_VARIANTS:
            clean_params = _clean_params(client, params)
            log(f"Trying {endpoint} params={clean_params}")
            try:
                payload = client.get(endpoint, params=clean_params)
                summary = _summarize_payload(payload)
                attempt = {
                    "endpoint": endpoint,
                    "params": clean_params,
                    **summary,
                }
            except Exception as exc:  # diagnostic tool; capture all provider exceptions
                attempt = {
                    "endpoint": endpoint,
                    "params": clean_params,
                    "valid": False,
                    "kind": "exception",
                    "error_message": str(exc),
                    "size": 0,
                    "keys": [],
                }

            attempts.append(attempt)
            if attempt.get("valid") and first_valid is None:
                first_valid = attempt
                log(f"VALID: {endpoint} params={clean_params}")
                return {
                    "capability": capability,
                    "status": "available",
                    "selected_endpoint": endpoint,
                    "selected_params": clean_params,
                    "attempts": attempts,
                }

    return {
        "capability": capability,
        "status": "unavailable",
        "selected_endpoint": None,
        "selected_params": None,
        "attempts": attempts,
    }


def main() -> None:
    log_header("FANTRAX PROVIDER CAPABILITY DISCOVERY")
    client = FantraxClient()

    results: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": "Fantrax",
        "workspace": {
            "name": client.workspace_name,
            "league_id": client.league_id,
            "sport": client.sport,
            "season": client.season,
        },
        "base_url": client.base_url,
        "capabilities": {},
    }

    for capability, endpoints in CAPABILITY_CANDIDATES.items():
        results["capabilities"][capability] = discover_capability(client, capability, endpoints)

    write_json(DISCOVERY_LOG, results)

    available = [key for key, value in results["capabilities"].items() if value.get("status") == "available"]
    unavailable = [key for key, value in results["capabilities"].items() if value.get("status") != "available"]

    log("")
    log_section("Discovery Summary")
    log(f"Available: {len(available)}")
    for item in available:
        selected = results["capabilities"][item]
        log(f"  - {item}: {selected.get('selected_endpoint')} {selected.get('selected_params')}")

    log(f"Unavailable: {len(unavailable)}")
    for item in unavailable:
        log(f"  - {item}")

    log("")
    log(f"Discovery log: {DISCOVERY_LOG}")
    log("No Raw files were overwritten.")


if __name__ == "__main__":
    main()
