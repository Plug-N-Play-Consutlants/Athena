"""
Scout context loader.

Scout is the first experience layer powered by Athena Engine. This module only
reads Athena outputs. It does not parse provider payloads and does not perform
business logic that belongs in Athena.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from Core.json_utils import read_optional_json
from Core.project_paths import OUTPUT_DIR, RAW_DIR, REPORTS_DIR


@dataclass
class ScoutContext:
    league_profile: Any = None
    knowledge_readiness: Any = None
    team_profiles: List[Dict[str, Any]] | None = None
    manager_behavior: Dict[str, Any] | None = None
    league_market: Dict[str, Any] | None = None
    transaction_history: Dict[str, Any] | None = None
    player_contracts: Dict[str, Any] | None = None
    player_master: List[Dict[str, Any]] | None = None
    raw_league_info: Dict[str, Any] | None = None
    raw_status: Dict[str, bool] | None = None

    @property
    def files_loaded(self) -> List[str]:
        loaded = []
        for name, value in self.__dict__.items():
            if name == "raw_status":
                continue
            if value not in (None, [], {}):
                loaded.append(name)
        return loaded


def _read(path: Path) -> Any:
    try:
        return read_optional_json(path)
    except Exception:
        return None


def load_context() -> ScoutContext:
    """Load current Athena outputs for Scout's deterministic responses."""
    raw_files = [
        RAW_DIR / "league_info.json",
        RAW_DIR / "fantrax_player_pool.json",
        RAW_DIR / "transactions.json",
    ]

    return ScoutContext(
        league_profile=_read(OUTPUT_DIR / "league_profile.json"),
        knowledge_readiness=_read(OUTPUT_DIR / "knowledge_readiness.json"),
        team_profiles=_read(OUTPUT_DIR / "team_profiles.json") or [],
        manager_behavior=_read(OUTPUT_DIR / "manager_behavior.json") or {},
        league_market=_read(OUTPUT_DIR / "league_market.json") or {},
        transaction_history=_read(OUTPUT_DIR / "transaction_history.json") or {},
        player_contracts=_read(OUTPUT_DIR / "player_contracts.json") or {},
        player_master=_read(OUTPUT_DIR / "player_master.json") or [],
        raw_league_info=_read(RAW_DIR / "league_info.json") or {},
        raw_status={path.name: path.exists() for path in raw_files},
    )


def get_team_names(ctx: ScoutContext) -> List[str]:
    return sorted([team.get("team_name", "") for team in (ctx.team_profiles or []) if team.get("team_name")])


def find_team(ctx: ScoutContext, query: str) -> Optional[Dict[str, Any]]:
    """Find a team by exact/partial name in current team profiles."""
    teams = ctx.team_profiles or []
    q = (query or "").lower().strip()
    if not q:
        return None

    for team in teams:
        name = str(team.get("team_name") or "").lower()
        if q == name:
            return team

    for team in teams:
        name = str(team.get("team_name") or "").lower()
        if q in name or name in q:
            return team

    return None


def league_average_team_value(ctx: ScoutContext) -> Optional[float]:
    values = [float(team.get("total_asset_value") or 0) for team in (ctx.team_profiles or []) if team.get("total_asset_value")]
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def league_average_asset_value(ctx: ScoutContext) -> Optional[float]:
    values = [float(team.get("average_asset_value") or 0) for team in (ctx.team_profiles or []) if team.get("average_asset_value")]
    if not values:
        return None
    return round(sum(values) / len(values), 3)
