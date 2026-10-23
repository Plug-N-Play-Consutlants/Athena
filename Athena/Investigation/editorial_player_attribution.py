"""Period-bounded NHL contributor / fantasy-team editorial bridge.

A numerically reconciled historical ACTIVE roster is not independently
proven game-effective Fantrax fantasy credit. Never flatten that distinction.
"""
from __future__ import annotations


def editorial_contributors(attribution: dict, nhl: dict) -> dict:
    result = {"status": "unavailable", "records": [],
              "interpretation": "No validated player-to-historical-team link"}
    if not isinstance(attribution, dict) or not isinstance(nhl, dict):
        return result
    if not nhl.get("verified") or attribution.get("period") != nhl.get("period"):
        return result
    if attribution.get("status") not in ("reconciled", "partial"):
        return result
    nhl_by_id = {str(p.get("fantrax_player_id")): p for p in nhl.get("records", [])
                 if isinstance(p, dict) and p.get("fantrax_player_id")}
    records = []
    for team in attribution.get("teams", []):
        if not isinstance(team, dict) or team.get("status") != "reconciled" or not team.get("identity_complete"):
            continue
        if team.get("lineup_eligibility") != "period_snapshot_not_game_effective":
            continue
        if team.get("difference") != 0 or not team.get("numeric_match"):
            continue
        for player in team.get("all_scoring_contributors", []):
            if not isinstance(player, dict) or type(player.get("points")) is not int or player["points"] <= 0:
                continue
            full = nhl_by_id.get(str(player.get("player_id")))
            if not full or any(player.get(k) != full.get(k) for k in ("points", "goals", "assists")):
                continue
            records.append({
                "player_name": player.get("name") or full.get("player_name"),
                "fantrax_player_id": str(player["player_id"]),
                "nhl_player_id": full.get("nhl_player_id"),
                "fantasy_team": team.get("team_name"),
                "fantasy_team_id": team.get("team_id"),
                "goals": player["goals"], "assists": player["assists"],
                "points": player["points"], "games_played": player.get("games_played"),
                "team_period_points": team.get("fantrax_points"),
                "attribution_kind": "historical_active_snapshot_numeric_reconciliation",
                "credited_points_verified": False,
            })
    records.sort(key=lambda item: (-item["points"], -item["goals"], str(item["player_name"])))
    return {"status": "reconciled_snapshot" if records else "no_eligible_contributors",
            "period": attribution.get("period"), "records": records,
            "interpretation": "Historical ACTIVE roster and full numeric team reconciliation; game-effective lineup credit not independently verified"}
