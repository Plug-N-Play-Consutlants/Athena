"""Regression checks for the v0.7.10.2.7 four-inquiry corrective pass."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Athena.intent_planner import plan_capability
from Athena.public_identity import resolve_public_player
from Knowledge.Intelligence.Public.public_player_profiles import profile_for_entity
from Athena.Investigation.period_standings import compare_periods

def run():
    q = "How has William Nylander performed this season, and what does that tell us about his contribution to the Maple Leafs?"
    plan = plan_capability(q, "public")
    assert plan and plan.route == "public_player_investigation", plan
    match = resolve_public_player(q)
    assert match and match.entity and match.entity.canonical_name == "William Nylander", match
    assert profile_for_entity(match.entity) is not None
    roster = plan_capability("What are the Maple Leafs' biggest roster needs, and how much flexibility do they have to address them?", "public")
    assert roster and roster.route == "public_nhl_team_economic_state"
    snapshots = [{"period": i, "teams": [{"team_id": "a", "name": "A", "rank": 4-i, "points": 10*i}]} for i in (1,2,3)]
    result = compare_periods(snapshots, requested_period=3, season_to_date=True)
    assert result["baseline_period"] == 1 and result["teams"][0]["rank_change"] == 2
    print("PASS: Nylander identity, roster route, season-to-date standings baseline")
if __name__ == "__main__":
    run()
