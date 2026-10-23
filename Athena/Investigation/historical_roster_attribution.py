"""Fantrax period rosters and conservative league scoring reconciliation.

A historical getTeamRosters(period=N) response records roster membership and
ACTIVE/RESERVE status. It is not evidence of game-by-game transaction effects;
only exact team total reconciliation can elevate an NHL attribution candidate.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path
import json
import re
from typing import Any

from Core.project_paths import OUTPUT_DIR


_STATUSES = {"ACTIVE", "RESERVE", "INJURED_RESERVE"}


def _valid_identity(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[A-Za-z0-9]+", value))


def normalize_period_rosters(payload: Any, *, league_id: str, season: Any, period: int,
                             expected_teams: int | None = None,
                             team_ids: set[str] | None = None) -> dict:
    """Reject wrong-period, partial, duplicate, and ambiguous provider responses."""
    if league_id is None or not _valid_identity(str(league_id)) or not str(season).isdigit() or type(period) is not int or period < 1:
        raise ValueError("Invalid historical roster archive identity")
    if not isinstance(payload, dict) or isinstance(payload.get("period"), bool):
        raise ValueError("Historical roster response lacks explicit period")
    try:
        provider_period = int(payload["period"])
    except (TypeError, ValueError, KeyError):
        raise ValueError("Historical roster response lacks valid period") from None
    if provider_period != period:
        raise ValueError(f"Historical roster provider returned period {provider_period}, requested {period}")
    rosters = payload.get("rosters")
    if not isinstance(rosters, dict) or not rosters:
        raise ValueError("Historical roster response lacks team rosters")
    if expected_teams is not None and len(rosters) != expected_teams:
        raise ValueError("Historical roster response has incomplete team coverage")
    if team_ids is not None and set(rosters) != team_ids:
        raise ValueError("Historical roster response team IDs differ from league metadata")
    records, teams, seen_players = [], [], set()
    for team_id, team in rosters.items():
        if not _valid_identity(team_id) or not isinstance(team, dict):
            raise ValueError("Historical roster team identity or object invalid")
        name = team.get("teamName")
        items = team.get("rosterItems")
        if not isinstance(name, str) or not name.strip() or not isinstance(items, list):
            raise ValueError("Historical roster team name or player list missing")
        teams.append({"team_id": team_id, "team_name": name.strip(), "player_count": len(items)})
        for item in items:
            if not isinstance(item, dict) or not _valid_identity(str(item.get("id") or "")):
                raise ValueError("Historical roster player ID missing")
            player_id = str(item["id"])
            if player_id in seen_players:
                raise ValueError("Historical player appears on multiple rosters")
            seen_players.add(player_id)
            status = item.get("status")
            if not isinstance(status, str) or status.upper() not in _STATUSES:
                raise ValueError(f"Unknown historical lineup status for {player_id}")
            position = item.get("position")
            if not isinstance(position, str) or not position:
                raise ValueError("Historical roster lacks lineup position")
            records.append({
                "player_id": player_id,
                "owner_team_id": team_id,
                "owner_team": name.strip(),
                "roster_status": status.upper(),
                "position": position.strip(),
                "active_for_period": status.upper() == "ACTIVE",
            })
    return {
        "schema": "athena.fantrax_period_rosters.v1",
        "status": "verified_period_rosters", "verified": True,
        "league_id": str(league_id), "season": str(season), "period": period,
        "source": "fantrax_fxea_general_getTeamRosters_period",
        "team_count": len(teams), "player_count": len(records),
        "active_count": sum(r["active_for_period"] for r in records),
        "teams": teams, "records": records,
        "interpretation": "Provider historical period roster and ACTIVE flags, not game-by-game credited fantasy points",
    }


def roster_path(output: Path, league_id: str, season: Any, period: int) -> Path:
    if league_id is None or not _valid_identity(str(league_id)) or not str(season).isdigit() or type(period) is not int or period < 1:
        raise ValueError("Invalid roster archive path identity")
    return Path(output) / "PeriodRosters" / str(league_id) / str(season) / f"period_{period:03d}.json"


def _valid_cached(data: Any, league_id: str, season: Any, period: int, expected_teams: int | None) -> bool:
    if not isinstance(data, dict) or data.get("schema") != "athena.fantrax_period_rosters.v1" or data.get("verified") is not True:
        return False
    if data.get("league_id") != str(league_id) or data.get("season") != str(season) or data.get("period") != period:
        return False
    records, teams = data.get("records"), data.get("teams")
    if not isinstance(records, list) or not records or not isinstance(teams, list) or not teams:
        return False
    if expected_teams is not None and len(teams) != expected_teams:
        return False
    if any(not isinstance(t, dict) or not _valid_identity(str(t.get("team_id") or "")) for t in teams):
        return False
    ids = [r.get("player_id") for r in records if isinstance(r, dict)]
    return (len(ids) == len(records) and len(set(ids)) == len(records) and
            all(isinstance(r, dict) and r.get("roster_status") in _STATUSES and
                isinstance(r.get("active_for_period"), bool) and
                r["active_for_period"] == (r["roster_status"] == "ACTIVE") for r in records) and
            data.get("player_count") == len(records) and
            data.get("team_count") == len(teams))


def acquire_period_rosters(*, league_id: str | None, season: Any, period: int | None,
                           expected_teams: int | None = None,
                           team_ids: set[str] | None = None,
                           output_dir: Path | None = None, client_factory=None,
                           clock: datetime | None = None, max_cache_age: timedelta = timedelta(hours=6)) -> dict:
    result = {"status": "not_attempted", "verified": False, "records": [], "reason": ""}
    if not league_id or type(period) is not int or period < 1:
        return {**result, "reason": "League and period required"}
    now = clock or datetime.now(timezone.utc)
    if now.tzinfo is None:
        return {**result, "reason": "Offset-aware clock required"}
    try:
        path = roster_path(Path(output_dir) if output_dir is not None else OUTPUT_DIR, league_id, season, period)
        if path.exists():
            try:
                cached = json.loads(path.read_text(encoding="utf-8"))
                stamp = datetime.fromisoformat(cached.get("acquired_at", ""))
                if (_valid_cached(cached, league_id, season, period, expected_teams) and
                        (team_ids is None or {t.get("team_id") for t in cached["teams"]} == team_ids) and
                        stamp.tzinfo and timedelta(0) <= now - stamp < max_cache_age):
                    return {**cached, "cached": True}
            except (ValueError, TypeError, KeyError, AttributeError):
                pass  # Bad archive must trigger a provider refresh, not a false success.
        if client_factory is None:
            from Providers.Fantrax.fantrax_client import FantraxClient
            client_factory = FantraxClient
        client = client_factory(league_id=league_id, season=season)
        payload = client.get_team_rosters(period)
        # Fantrax may return an auth challenge as a JSON object. It can never
        # be accepted without a returned period and complete rosters.
        validated = normalize_period_rosters(payload, league_id=league_id, season=season, period=period,
                                             expected_teams=expected_teams, team_ids=team_ids)
        validated["acquired_at"] = now.isoformat()
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(validated, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(path)
        return validated
    except (ValueError, KeyError, OSError, TypeError, ImportError) as exc:
        return {**result, "status": "unverified_period_roster", "reason": str(exc)[:180]}
    except Exception as exc:
        return {**result, "status": "provider_unavailable", "reason": f"{type(exc).__name__} acquiring historical rosters"}


def backfill_period_rosters(*, league_id: str | None, season: Any, through_period: int | None,
                           expected_teams: int | None = None, output_dir: Path | None = None,
                           client_factory=None, clock: datetime | None = None) -> dict:
    """Backfill only completed periods, bounded to avoid unbounded API calls."""
    if type(through_period) is not int or through_period < 1:
        return {"status": "not_attempted", "periods": {}, "verified_count": 0}
    periods = {}
    # At most four historical requests per inquiry; rest are populated by future
    # syncs or targeted inquiries. Supports Weeks 1-3 in a single acceptance.
    for period in range(max(1, through_period - 3), through_period + 1):
        periods[period] = acquire_period_rosters(
            league_id=league_id, season=season, period=period,
            expected_teams=expected_teams, output_dir=output_dir,
            client_factory=client_factory, clock=clock)
    count = sum(1 for r in periods.values() if r.get("verified"))
    return {"status": "verified" if count == len(periods) else "partial" if count else "unverified",
            "periods": periods, "verified_count": count}


def reconcile_period_points(rosters: dict, nhl: dict, comparison: dict) -> dict:
    """Explain team scoring conservatively, with an exact Fantrax delta.

    Only 'reconciled' teams with full active-player identity coverage and exact
    points equality can be characterized as credited contributions. Other teams
    receive candidates with a clear discrepancy or coverage warning.
    """
    if not rosters.get("verified") or not nhl.get("verified") or comparison.get("status") != "compared":
        return {"status": "incomplete", "teams": [], "reason": "Historical rosters, NHL production and comparable Fantrax standings required"}
    if rosters.get("period") != nhl.get("period") or rosters.get("period") != comparison.get("period"):
        return {"status": "wrong_period", "teams": [], "reason": "Period identities do not match"}
    for source in (nhl, comparison):
        if source.get("league_id") is not None and str(source["league_id"]) != str(rosters.get("league_id")):
            return {"status": "wrong_source", "teams": [], "reason": "League identity differs across scoring evidence"}
        if source.get("season") is not None and str(source["season"]) != str(rosters.get("season")):
            return {"status": "wrong_source", "teams": [], "reason": "Season identity differs across scoring evidence"}
    crosswalk_ids = set(nhl.get("roster_crosswalk_ids") or [])
    player_scores = {str(r["fantrax_player_id"]): r for r in nhl.get("records", [])
                     if isinstance(r, dict) and r.get("fantrax_player_id")}
    roster_by_team = {}
    for row in rosters["records"]:
        roster_by_team.setdefault(row["owner_team_id"], []).append(row)
    results = []
    # The NHL source is a league-wide skater view. Players on RESERVE and IR
    # can have real NHL points, but must never enter an ACTIVE team subtotal.
    for team in comparison.get("teams", []):
        team_id = str(team.get("team_id") or "")
        roster_entries = roster_by_team.get(team_id)
        if roster_entries is None:
            return {"status": "incomplete", "teams": [], "reason": "Standings team not present in historical roster"}
        active = [r for r in roster_entries if r["active_for_period"]]
        contributors, unmatched, no_nhl_game_rows = [], [], []
        for r in active:
            production = player_scores.get(r["player_id"])
            if production is None:
                # NHL summary may not include a non-scoring player. A resolved
                # crosswalk proves identity, not necessarily a played game.
                if r["player_id"] not in crosswalk_ids:
                    unmatched.append(r["player_id"])
                else:
                    no_nhl_game_rows.append(r["player_id"])
                continue
            if production.get("points", 0) > 0:
                contributors.append({"player_id": r["player_id"],
                                     "name": production["player_name"],
                                     "points": production["points"], "goals": production["goals"],
                                     "assists": production["assists"],
                                     "games_played": production["games_played"]})
        contributors.sort(key=lambda r: (-r["points"], r["name"]))
        reserve_production = []
        for entry in roster_entries:
            if entry["active_for_period"]:
                continue
            produced = player_scores.get(entry["player_id"])
            if produced is not None and produced.get("points", 0) > 0:
                reserve_production.append({
                    "player_id": entry["player_id"],
                    "name": produced.get("player_name", ""),
                    "roster_status": entry["roster_status"],
                    "nhl_points_excluded": produced["points"],
                })
        reserve_production.sort(key=lambda row: (-row["nhl_points_excluded"], row["player_id"]))
        scored = sum(p["points"] for p in contributors)
        published = team.get("period_points")
        verified_total = type(published) in (int, float)
        delta = round(published - scored, 6) if verified_total else None
        # Exact agreement confirms the numeric total. Missing zero scorers are
        # still an identity coverage gap, not proof of an absent player.
        status = ("not_comparable" if not verified_total else
                  "reconciled_with_identity_gaps" if delta == 0 and unmatched else
                  "reconciled" if delta == 0 else "discrepancy")
        exceptions = []
        if unmatched:
            exceptions.append({"type": "unresolved_active_identity", "player_ids": sorted(unmatched),
                               "detail": "No verified NHL identity; missing NHL scoring is possible but not established"})
        if verified_total and delta != 0:
            exceptions.append({"type": "point_difference", "points": delta,
                               "detail": "NHL G+A from the period snapshot differs from Fantrax period points; source or eligibility requires investigation"})
        if not verified_total:
            exceptions.append({"type": "fantrax_total_unavailable"})
        # A period-snapshot ACTIVE designation is not a validated game-by-game
        # lineup ledger, even when the numeric team total happens to agree.
        results.append({"team_id": team_id, "team_name": (team.get("name") or (active[0]["owner_team"] if active else team_id)),
                        "status": status, "fantrax_points": published,
                        "identified_active_nhl_points": scored, "difference": delta,
                        "active_roster_count": len(active), "unmatched_active_ids": unmatched,
                        "active_ids_without_nhl_game_rows": no_nhl_game_rows,
                        "identity_complete": not unmatched, "numeric_match": verified_total and delta == 0,
                        "lineup_eligibility": "period_snapshot_not_game_effective",
                        "credited_fantasy_points_verified": False,
                        "reserve_nhl_points_excluded": sum(x["nhl_points_excluded"] for x in reserve_production),
                        "reserve_contributors_excluded": reserve_production,
                        "exceptions": exceptions,
                        "contributors": contributors[:10],
                        "all_scoring_contributors": contributors})
    reconciled = sum(r["status"] == "reconciled" for r in results)
    numeric_matched = sum(r["difference"] == 0 for r in results)
    return {"schema": "athena.period_attribution.v1", "status": "reconciled" if reconciled == len(results) else "partial",
            "period": rosters["period"], "team_count": len(results),
            "fully_reconciled_teams": reconciled, "numeric_matched_teams": numeric_matched,
            "unmatched_active_ids": sorted({pid for t in results for pid in t["unmatched_active_ids"]}),
            "teams_with_identity_gaps": sum(bool(t["unmatched_active_ids"]) for t in results),
            "teams_with_point_discrepancies": sum(t["status"] == "discrepancy" for t in results),
            "total_absolute_unexplained_points": sum(abs(t["difference"]) for t in results if t["difference"] is not None),
            "reserve_nhl_points_excluded": sum(t["reserve_nhl_points_excluded"] for t in results),
            "eligibility_evidence": "period_roster_snapshot_only_not_game_effective",
            "teams": results,
            "interpretation": "Numeric agreement between NHL G+A for snapshot ACTIVE players and Fantrax team-period points; even exact totals cannot independently verify game-effective lineup credit"}
