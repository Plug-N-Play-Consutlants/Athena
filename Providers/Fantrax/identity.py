"""Fantrax league identity resolution helpers."""
from __future__ import annotations

import re
from typing import Any

from Core.json_utils import read_optional_json
from Core.project_paths import OUTPUT_DIR

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def _usable_name(value: Any) -> str:
    text = str(value or "").strip()
    if not text or text.lower() == "unknown" or _EMAIL_RE.match(text):
        return ""
    return text

def resolve_league_name(payload: Any, fallback: str = "") -> str:
    """Resolve a display league name without mistaking Fantrax profile email for it.

    Fantrax can return the account email in leagueName for a current-season
    league payload. When that occurs, preserve league continuity by matching
    leagueHistoryId to existing canonical league archetype knowledge.
    """
    if not isinstance(payload, dict):
        return _usable_name(fallback) or "unknown"
    direct = _usable_name(payload.get("leagueName") or payload.get("name"))
    if direct:
        return direct
    history_id = str(payload.get("leagueHistoryId") or "").strip()
    historical = read_optional_json(OUTPUT_DIR / "league_archetype.json")
    if isinstance(historical, dict):
        historical_id = str(historical.get("league_history_id") or historical.get("league_id") or "").strip()
        historical_name = _usable_name(historical.get("league_name"))
        if history_id and historical_id == history_id and historical_name:
            return historical_name
    return _usable_name(fallback) or "unknown"
