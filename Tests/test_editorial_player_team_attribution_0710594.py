from Athena.Investigation.editorial_player_attribution import editorial_contributors
from Scout.conversation.journalist_composition import compose_journalist_report


def fixtures():
    nhl = {"verified": True, "period": 3, "records": [
        {"fantrax_player_id": "a", "nhl_player_id": "10", "player_name": "Star A", "points": 10, "goals": 6, "assists": 4},
        {"fantrax_player_id": "b", "nhl_player_id": "11", "player_name": "Reserve B", "points": 12, "goals": 8, "assists": 4},
        {"fantrax_player_id": "c", "nhl_player_id": "12", "player_name": "Star C", "points": 9, "goals": 3, "assists": 6},
    ]}
    def team(name, pid, points, state="reconciled"):
        p = next(x for x in nhl["records"] if x["fantrax_player_id"] == pid)
        return {"team_id": name, "team_name": name, "status": state,
                "identity_complete": True, "lineup_eligibility": "period_snapshot_not_game_effective",
                "difference": 0, "numeric_match": True, "fantrax_points": points,
                "all_scoring_contributors": [{"player_id": pid, "name": p["player_name"],
                                               "points": p["points"], "goals": p["goals"],
                                               "assists": p["assists"]}]}
    attribution = {"status": "partial", "period": 3,
                   "teams": [team("Leeeroy Jenkins", "a", 47), team("Bad source", "c", 38, "discrepancy")]}
    research = {"schema": "athena.league_period_research.v2", "league_name": "JHLPAA", "period": 3,
                "findings": [{"kind": "scoring_leader", "team": "Leeeroy Jenkins", "period_points": 47}],
                "nhl_player_leaders": nhl["records"]}
    return nhl, attribution, research


def test_joins_reconciled_active_only_and_excludes_reserve_and_discrepant_teams():
    nhl, attribution, _ = fixtures()
    out = editorial_contributors(attribution, nhl)
    assert out["status"] == "reconciled_snapshot"
    assert len(out["records"]) == 1
    assert out["records"][0]["fantasy_team"] == "Leeeroy Jenkins"
    assert out["records"][0]["player_name"] == "Star A"
    assert out["records"][0]["credited_points_verified"] is False
    assert "Reserve B" not in str(out) and "Star C" not in str(out)


def test_newsroom_names_team_without_claiming_independent_credit():
    nhl, attribution, research = fixtures()
    research["editorial_player_attribution"] = editorial_contributors(attribution, nhl)
    report = compose_journalist_report(research=research)
    assert "JHLPAA player spotlight" in report
    assert "Star A (10 G+A)" in report and "Leeeroy Jenkins's archived ACTIVE roster" in report
    assert "does not independently prove game-by-game fantasy eligibility" in report
    assert "Reserve B" not in report and "Star C" not in report


def test_missing_wrong_period_or_mismatched_scoring_fails_closed():
    nhl, attribution, research = fixtures()
    assert editorial_contributors(attribution, {**nhl, "period": 2})["records"] == []
    attribution["teams"][0]["all_scoring_contributors"][0]["points"] = 11
    assert editorial_contributors(attribution, nhl)["records"] == []
    research["editorial_player_attribution"] = {"status": "reconciled_snapshot", "period": 2, "records": [{"player_name": "Wrong period", "fantasy_team": "Team", "points": 12, "credited_points_verified": False, "attribution_kind": "historical_active_snapshot_numeric_reconciliation"}]}
    report = compose_journalist_report(research=research)
    assert "Wrong period" not in report
    assert "NHL spotlight" in report
