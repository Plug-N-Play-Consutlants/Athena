"""
NHL public data provider client.

Provider responsibility:
- Communicate with public NHL data endpoints.
- Return raw provider payloads.
- No fantasy league logic.
- No canonical normalization.

This client uses direct HTTP calls for stability. The nhl-api-py package can be
used later as a convenience wrapper, but the engine should not depend on wrapper
method names for core provider capability.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any
from urllib.parse import quote


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import requests

from Core.json_utils import write_json
from Core.logger import log
from Core.project_paths import RAW_DIR


class NHLClient:
    """Minimal public NHL provider client."""

    def __init__(self) -> None:
        self.web_base_url = "https://api-web.nhle.com/v1"
        self.stats_base_url = "https://api.nhle.com/stats/rest/en"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Sports Intelligence Engine 2.0"})

    def get_web(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.web_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        response = self.session.get(url, params=params or {}, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_stats(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.stats_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        response = self.session.get(url, params=params or {}, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_skater_summary(self, season_id: str, game_type_id: int = 2, limit: int = -1) -> Any:
        cayenne_exp = f"seasonId={season_id} and gameTypeId={game_type_id}"
        return self.get_stats(
            "skater/summary",
            params={
                "limit": limit,
                "cayenneExp": cayenne_exp,
            },
        )

    def get_skater_game_log(self, player_id: str, season: str, game_type: int = 2) -> Any:
        return self.get_web(f"player/{player_id}/game-log/{season}/{game_type}")

    def get_player_landing(self, player_id: str) -> Any:
        return self.get_web(f"player/{player_id}/landing")

    def save_raw_json(self, filename: str, payload: Any) -> None:
        path = RAW_DIR / filename
        write_json(path, payload)
        log(f"Saved raw payload: {path}")
