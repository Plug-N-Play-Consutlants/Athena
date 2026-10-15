"""Current NHL team performance acquisition and bounded assessment.

Never substitutes seeded team identity for current-season results.
"""
from __future__ import annotations
from datetime import date
from typing import Any


def assess_team_performance(question: str, abbreviation: str, name: str) -> dict[str, Any]:
    from Providers.NHL.nhl_client import NHLClient
    from Knowledge.Intelligence.Public.player_evidence import _target_season_id
    season = _target_season_id()
    evidence: dict[str, Any] = {"season": season, "team": abbreviation, "sources": [], "missing": []}
    try:
        payload = NHLClient().get_club_stats(abbreviation, season)
        if not isinstance(payload, dict): raise ValueError("unexpected_club_stats_payload")
        evidence["sources"].append("nhl_club_stats_season")
        skaters = payload.get("skaters") or []
        goalies = payload.get("goalies") or []
        if not isinstance(skaters, list): skaters = []
        if not isinstance(goalies, list): goalies = []
        skaters = [r for r in skaters if isinstance(r, dict) and isinstance(r.get("gamesPlayed"), (int,float)) and r["gamesPlayed"] > 0]
        ranked = sorted(skaters, key=lambda r: (r.get("points") if isinstance(r.get("points"), (int,float)) else -1), reverse=True)
        leaders = []
        for row in ranked[:5]:
            name_parts = [str(row.get(k) or "") for k in ("firstName", "lastName")]
            name_parts = [x.get("default", "") if isinstance(x, dict) else x for x in (row.get("firstName"), row.get("lastName"))]
            label = " ".join(x for x in name_parts if x).strip()
            if label:
                leaders.append({"name": label, "gp": row.get("gamesPlayed"), "goals": row.get("goals"), "assists": row.get("assists"), "points": row.get("points")})
        evidence["leaders"] = leaders
        evidence["skaters_observed"] = len(skaters)
        evidence["goalies_observed"] = len(goalies)
    except Exception as exc:
        evidence["missing"].append("verified_current_season_club_stats")
        evidence["acquisition_error"] = type(exc).__name__
    # Team-level results are distinct from individual scoring. Keep each source
    # independent so a failed standings endpoint does not erase verified players.
    try:
        standings_payload = NHLClient().get_team_standings_now()
        rows = standings_payload.get("standings") if isinstance(standings_payload, dict) else None
        if not isinstance(rows, list):
            raise ValueError("standings_rows_missing")
        match = next((r for r in rows if isinstance(r, dict) and
                      str(r.get("teamAbbrev", {}).get("default", "") if isinstance(r.get("teamAbbrev"), dict) else r.get("teamAbbrev", "")).upper() == abbreviation.upper()), None)
        if match is None:
            raise ValueError("team_not_in_standings")
        keys = ("gamesPlayed", "wins", "losses", "otLosses", "points", "pointPctg", "goalFor", "goalAgainst", "streakCode", "streakCount", "last10Wins", "last10Losses", "last10OtLosses")
        evidence["standings"] = {key: match[key] for key in keys if isinstance(match.get(key), (int, float, str))}
        evidence["sources"].append("nhl_official_current_standings")
    except Exception as exc:
        evidence["missing"].append("verified_current_team_standings")
        evidence["standings_acquisition_error"] = type(exc).__name__
    try:
        schedule = NHLClient().get_team_schedule_now(abbreviation)
        games = schedule.get("games") if isinstance(schedule, dict) else None
        if not isinstance(games, list):
            raise ValueError("schedule_games_missing")
        completed = []
        for game in games:
            if not isinstance(game, dict) or game.get("gameState") not in ("OFF", "FINAL"):
                continue
            home, away = game.get("homeTeam") or {}, game.get("awayTeam") or {}
            if not isinstance(home, dict) or not isinstance(away, dict):
                continue
            hs, aws = home.get("score"), away.get("score")
            if not isinstance(hs, int) or not isinstance(aws, int):
                continue
            is_home = home.get("abbrev") == abbreviation
            if not is_home and away.get("abbrev") != abbreviation:
                continue
            completed.append({"date": game.get("gameDate"), "opponent": away.get("abbrev") if is_home else home.get("abbrev"), "for": hs if is_home else aws, "against": aws if is_home else hs})
        completed.sort(key=lambda g: str(g["date"] or ""))
        evidence["recent_games"] = completed[-5:]
        if completed:
            evidence["sources"].append("nhl_official_completed_games")
        else:
            evidence["missing"].append("verified_recent_completed_games")
    except Exception as exc:
        evidence["missing"].append("verified_recent_completed_games")
        evidence["schedule_acquisition_error"] = type(exc).__name__
    # Compose the existing roster and economics capabilities only when the question
    # calls for them. Roster membership does not establish deployment or need.
    wants_roster = any(term in question.casefold() for term in
        ("roster", "lineup", "depth", "need", "weakness", "trade", "cap", "salary", "improv"))
    if wants_roster:
        try:
            roster = NHLClient().get_current_roster(abbreviation)
            if not isinstance(roster, dict):
                raise ValueError("unexpected_roster_payload")
            groups = ("forwards", "defensemen", "goalies")
            counts = {key: len(roster[key]) for key in groups if isinstance(roster.get(key), list)}
            if not counts:
                raise ValueError("roster_groups_missing")
            evidence["roster_counts"] = counts
            # A positional inventory is useful context but is not deployment,
            # quality, injury status, or evidence of a shortage.
            positions = {}
            for group in groups:
                for player in roster.get(group) or []:
                    if isinstance(player, dict):
                        pos = str(player.get("positionCode") or "").upper()
                        if pos in ("C", "L", "R", "D", "G"):
                            positions[pos] = positions.get(pos, 0) + 1
            if positions:
                evidence["roster_positions"] = positions
            evidence["sources"].append("nhl_current_roster")
        except Exception as exc:
            evidence["missing"].append("verified_current_roster")
            evidence["roster_acquisition_error"] = type(exc).__name__
        try:
            from Knowledge.Teams.team_economic_state import resolve_team_economic_state
            from Knowledge.Economics.league_season_context import resolve_league_season_context
            state = resolve_team_economic_state(abbreviation=abbreviation)
            context = resolve_league_season_context()
            evidence["economics"] = {
                "league_year": context.league_year,
                "upper_limit": context.upper_limit,
                "contract_coverage": len(state.covered_contracts()),
                "aggregate_permitted": state.aggregate_permitted,
            }
            evidence["sources"].extend(["canonical_team_economic_state", "canonical_league_season_context"])
            if not state.aggregate_permitted:
                evidence["missing"].append("complete_verified_team_cap_ledger")
        except (LookupError, ValueError, OSError) as exc:
            evidence["missing"].append("canonical_team_economic_context")
            evidence["economic_acquisition_error"] = type(exc).__name__
        evidence["missing"].append("verified_roster_deployment_and_needs")
    else:
        evidence["missing"].append("verified_roster_deployment_and_cap_state")
    if evidence.get("leaders"):
        text = f"Official NHL {season} team player production for {name}: " + "; ".join(f"{r['name']} ({r['points']} points in {r['gp']} games)" for r in evidence["leaders"] if isinstance(r.get("points"),(int,float))) + "."
        text += " These are scoring contributors, not proof of overall team strength, weakness or causation. Standings, game trends, deployment and cap context remain necessary for a complete assessment."
        confidence = 0.56
    else:
        text = f"No verified {season} NHL team production was acquired for {name}. A current-season strengths-and-weaknesses assessment cannot be derived from a historical seed profile."
        confidence = 0.3
    standings = evidence.get("standings")
    if standings:
        text += f" Official standings: {standings.get('wins', '?')}-{standings.get('losses', '?')}-{standings.get('otLosses', '?')} in {standings.get('gamesPlayed', '?')} games, {standings.get('points', '?')} standings points."
        if isinstance(standings.get("goalFor"), int) and isinstance(standings.get("goalAgainst"), int):
            text += f" Goals for/against: {standings['goalFor']}/{standings['goalAgainst']}."
    recent = evidence.get("recent_games") or []
    if recent:
        wins = sum(g["for"] > g["against"] for g in recent)
        text += f" In the last {len(recent)} verified completed games: {wins} wins and {len(recent)-wins} non-wins (including possible overtime/shootout losses)."
    if wants_roster:
        counts = evidence.get("roster_counts")
        if counts:
            text += " The official current roster lists " + ", ".join(f"{value} {key}" for key, value in counts.items()) + "; these are roster counts, not proof of positional surplus or shortage."
        if evidence.get("roster_positions"):
            text += " Positional inventory: " + ", ".join(f"{key} {value}" for key, value in sorted(evidence["roster_positions"].items())) + "."
        economic = evidence.get("economics")
        if economic:
            text += f" The {economic['league_year']} NHL upper limit is ${economic['upper_limit']:,}."
            if not economic["aggregate_permitted"]:
                text += f" Canonical contract coverage includes {economic['contract_coverage']} contracts, not a complete club ledger; team cap usage and available space cannot be calculated reliably."
        text += " A specific roster need or acquisition recommendation requires verified deployment, health, performance and transaction context."
    return {"conclusion": text, "evidence": evidence, "confidence": confidence}


def official_team_player_row(player_name: str, team_name: str) -> dict[str, Any] | None:
    """Exact identity match in verified current NHL club-season statistics."""
    from Providers.NHL.nhl_client import NHLClient
    from Knowledge.Intelligence.Public.player_evidence import _target_season_id
    from Knowledge.Intelligence.Public.public_team_profiles import public_team_profiles
    import re
    aliases = {"toronto maple leafs": "TOR", "toronto": "TOR", "tor": "TOR"}
    team_key = str(team_name or "").strip().casefold()
    abbreviation = aliases.get(team_key)
    if abbreviation is None:
        for profile in public_team_profiles() or []:
            if str(getattr(profile, "display_name", "")).casefold() == team_key:
                abbreviation = str(getattr(profile, "abbreviation", "") or "").upper()
                break
    if not abbreviation or not re.fullmatch(r"[A-Z]{3}", abbreviation):
        return None
    season = _target_season_id()
    payload = NHLClient().get_club_stats(abbreviation, season)
    if not isinstance(payload, dict):
        return None
    wanted = " ".join(str(player_name).casefold().split())
    for row in payload.get("skaters") or []:
        if not isinstance(row, dict):
            continue
        parts = []
        for key in ("firstName", "lastName"):
            value = row.get(key)
            parts.append(str(value.get("default", "") if isinstance(value, dict) else value or ""))
        if " ".join(" ".join(parts).casefold().split()) != wanted:
            continue
        gp, points = row.get("gamesPlayed"), row.get("points")
        if not isinstance(gp, (int, float)) or gp <= 0 or not isinstance(points, (int, float)):
            return None
        return {"season": season, "gp": gp, "points": points, "goals": row.get("goals"), "assists": row.get("assists")}
    return None
