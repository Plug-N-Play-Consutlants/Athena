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
    evidence["missing"].extend(["verified_team_standings_and_game_trends", "verified_roster_deployment_and_cap_state"])
    if evidence.get("leaders"):
        text = f"Official NHL {season} team player production for {name}: " + "; ".join(f"{r['name']} ({r['points']} points in {r['gp']} games)" for r in evidence["leaders"] if isinstance(r.get("points"),(int,float))) + "."
        text += " These are scoring contributors, not proof of overall team strength, weakness or causation. Standings, game trends, deployment and cap context remain necessary for a complete assessment."
        confidence = 0.56
    else:
        text = f"No verified {season} NHL team production was acquired for {name}. A current-season strengths-and-weaknesses assessment cannot be derived from a historical seed profile."
        confidence = 0.3
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
