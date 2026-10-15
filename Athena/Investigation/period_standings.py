"""Period-aligned league standings evidence and trend calculations.

Only accepts already validated canonical standings snapshots; Fantrax payload
normalization must establish league, season, period and complete team identity.
"""
from __future__ import annotations
from typing import Any, Callable


def required_periods(period: int, *, season_to_date: bool = False) -> list[int]:
    if type(period) is not int or period < 1:
        raise ValueError("period must be a positive integer")
    return list(range(1, period + 1)) if season_to_date else list(range(max(1, period - 1), period + 1))


def compare_periods(snapshots: list[dict[str, Any]], *, requested_period: int, season_to_date: bool = False) -> dict[str, Any]:
    """Compare complete league-wide cumulative snapshots with stable team IDs.

    A missing baseline yields unavailable deltas, never an invented zero.
    """
    indexed: dict[int, dict[str, Any]] = {}
    for snapshot in snapshots:
        period = snapshot.get("period")
        if type(period) is not int or period < 1 or period in indexed:
            raise ValueError("invalid or duplicate standings period")
        teams = snapshot.get("teams")
        if not isinstance(teams, list) or not teams:
            raise ValueError("standings snapshot requires teams")
        identities = [str(t.get("team_id") or "").strip() for t in teams]
        if any(not i for i in identities) or len(set(identities)) != len(identities):
            raise ValueError("standings require unique stable team IDs")
        indexed[period] = snapshot
    if requested_period not in indexed:
        return {"status": "missing_requested_period", "period": requested_period, "teams": [], "missing_periods": [requested_period]}
    current = indexed[requested_period]
    baseline_period = 1 if season_to_date and requested_period > 1 else requested_period - 1
    prior = indexed.get(baseline_period)
    previous_teams = {str(t["team_id"]): t for t in prior["teams"]} if prior else {}
    rows = []
    for team in current["teams"]:
        tid = str(team["team_id"])
        before = previous_teams.get(tid)
        rank, points = team.get("rank"), team.get("points")
        old_rank, old_points = (before.get("rank"), before.get("points")) if before else (None, None)
        rank_change = old_rank - rank if type(rank) is int and type(old_rank) is int else None
        point_change = points - old_points if type(points) in (int, float) and type(old_points) in (int, float) else None
        rows.append({"team_id": tid, "name": team.get("name"), "rank": rank,
                     "points": points, "rank_change": rank_change, "period_points": point_change,
                     "baseline_available": before is not None})
    return {"status": "compared" if prior else "baseline_missing", "period": requested_period,
            "baseline_period": baseline_period if requested_period > 1 else None,
            "missing_periods": [baseline_period] if requested_period > 1 and not prior else [],
            "teams": rows, "source": "canonical_period_standings"}


def acquire_periods(period: int, fetch: Callable[[int], dict[str, Any]], *, season_to_date: bool = False) -> dict[str, Any]:
    """Provider-neutral period traversal; caller supplies validated canonical fetcher."""
    requested = required_periods(period, season_to_date=season_to_date)
    snapshots, failures = [], {}
    for p in requested:
        try:
            snapshot = fetch(p)
            if snapshot.get("period") != p:
                raise ValueError("provider returned a different scoring period")
            snapshots.append(snapshot)
        except (ValueError, KeyError, TypeError, OSError) as exc:
            failures[p] = str(exc)
    result = compare_periods(snapshots, requested_period=period, season_to_date=season_to_date)
    result["requested_periods"] = requested
    result["acquisition_errors"] = failures
    return result
