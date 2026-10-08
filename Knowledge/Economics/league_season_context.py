"""Resolve effective-dated NHL rules and core economic environment.

This module owns context, not team cap calculation. Contract and team-ledger
capabilities consume this state rather than duplicating league-year constants.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
import json
from pathlib import Path
from typing import Any, Dict, Optional

_ROOT = Path(__file__).resolve().parents[2]
_PACK = _ROOT / "Knowledge" / "Packs" / "NHL" / "economics"


@dataclass(frozen=True)
class LeagueSeasonContext:
    league: str
    league_year: str
    as_of: str
    cba_environment_id: str
    cba_label: str
    cba_effective_from: str
    cba_effective_to: str
    lower_limit: int
    midpoint: int
    upper_limit: int
    payroll_range_status: str
    provenance: tuple[Dict[str, Any], ...]
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _load(name: str) -> list[Dict[str, Any]]:
    payload = json.loads((_PACK / name).read_text(encoding="utf-8"))
    return [row for row in payload.get("records", []) if isinstance(row, dict)]


def _day(value: str | date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value).strip()[:10])


def league_year_for_day(day: date) -> str:
    start = day.year if day.month >= 7 else day.year - 1
    return f"{start}-{str(start + 1)[-2:]}"


def _contains(row: Dict[str, Any], day: date) -> bool:
    start = _day(row["effective_from"])
    end = _day(row["effective_to"]) if row.get("effective_to") else date.max
    return start <= day <= end


def resolve_league_season_context(*, as_of: str | date | datetime | None = None,
                                  league_year: Optional[str] = None) -> LeagueSeasonContext:
    """Resolve canonical NHL context for a date or league year.

    Date resolution is authoritative when supplied. A league-year-only request
    resolves at October 1 of that season so it represents the regular-season
    rules environment rather than an arbitrary calendar boundary.
    """
    if as_of is None and not league_year:
        as_of = date.today()
    if as_of is None:
        start_year = int(str(league_year).split("-")[0])
        day = date(start_year, 10, 1)
    else:
        day = _day(as_of)
    resolved_year = league_year_for_day(day)
    if league_year and str(league_year) != resolved_year:
        raise ValueError(f"as_of {day.isoformat()} belongs to {resolved_year}, not {league_year}")

    payroll = next((row for row in _load("payroll_ranges.json") if row.get("league_year") == resolved_year and _contains(row, day)), None)
    if payroll is None:
        raise LookupError(f"No canonical NHL payroll range registered for {resolved_year} on {day.isoformat()}")
    cba = next((row for row in _load("rule_environments.json") if _contains(row, day)), None)
    if cba is None:
        raise LookupError(f"No canonical NHL CBA environment registered for {day.isoformat()}")

    provenance = (
        {key: payroll.get(key) for key in ("source_id", "source_title", "authority", "source_url", "announced_on")},
        {key: cba.get(key) for key in ("source_id", "label", "authority", "source_url")},
    )
    limitations = (
        "LeagueSeasonContext supplies league-wide rules/economic state; it does not calculate a club ledger.",
        "Provision-level effective dates can supersede the general CBA environment and must be resolved by the rule capability that applies them.",
    )
    return LeagueSeasonContext(
        league="NHL", league_year=resolved_year, as_of=day.isoformat(),
        cba_environment_id=str(cba["environment_id"]), cba_label=str(cba["label"]),
        cba_effective_from=str(cba["effective_from"]), cba_effective_to=str(cba["effective_to"]),
        lower_limit=int(payroll["lower_limit"]), midpoint=int(payroll["midpoint"]), upper_limit=int(payroll["upper_limit"]),
        payroll_range_status=str(payroll.get("status") or "unknown"), provenance=provenance, limitations=limitations,
    )
