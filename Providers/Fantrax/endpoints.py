"""
Fantrax endpoint registry.

Provider-layer responsibility:
- Keep active Fantrax endpoint identifiers in one place.
- Keep provider-specific route names out of Build, Knowledge, and Intelligence.
- Allow Configuration/config.json overrides for active endpoints only.

Retired endpoint families are documented in Archive/retired_fantrax_legacy_endpoints_20260618.
"""

from __future__ import annotations

from typing import Any

from Core.config import get_config_value


class FantraxEndpoints:
    """Default Fantrax routes used by the active provider adapter."""

    # fxea REST-style routes verified in the current engine baseline.
    LEAGUE = "general/getLeagueInfo"
    PLAYER_POOL = "general/getTeamRosters"
    SCHEDULE = "schedule/getSchedule"
    PLAYER_STATS = "players/getPlayerStats"

    # Transactions are served through fxpa/req as a method call rather than fxea.
    TRANSACTIONS_METHOD = "getTransactionDetailsHistory"
    FXPA_REQUEST_URL = "https://www.fantrax.com/fxpa/req"

    CONFIG_KEYS = {
        "league": LEAGUE,
        "player_pool": PLAYER_POOL,
        "schedule": SCHEDULE,
        "player_stats": PLAYER_STATS,
    }

    @classmethod
    def get(cls, endpoint_name: str, default: Any = None) -> Any:
        fallback = cls.CONFIG_KEYS.get(endpoint_name, default)
        return get_config_value(f"provider.endpoints.{endpoint_name}", fallback)
