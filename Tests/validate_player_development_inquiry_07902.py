"""Offline regression for development routing and evidence-bounded analysis."""
from Athena.intent_planner import plan_capability
from Athena.execution_registry import SPECIALISTS
from Athena.player_development import analyze_player_development, _historical_levels
from Reasoning.Significance import assess_asset_significance, assess_organizational_significance

def run():
    prompt = ("Luke Haymes made the NHL at 23 after playing NCAA and AHL hockey. "
              "Is that actually late compared with relevant prospects, or is his development ahead "
              "of expectations? Consider players who never reach the NHL, his development pathway, "
              "roster opportunity, and what we can reasonably project about him today.")
    plan = plan_capability(prompt, "public")
    assert plan and plan.route == "public_player_development", plan
    assert plan.route in SPECIALISTS
    assert plan_capability("What's the biggest NHL story right now?", "public").route == "live_event_intelligence"
    player={"name":"Sample Prospect","age":23,"relationship":"current_roster","games_played":3,
            "draft":{"overall_pick":31}, "rights_state":{"control_status":"controlled"}}
    history=_historical_levels({"seasonTotals":[{"season":20242025,"leagueAbbrev":"NCAA","gamesPlayed":28},
                                                    {"season":20252026,"leagueAbbrev":"AHL","gamesPlayed":50}]})
    assert len(history)==2
    assessment=analyze_player_development(player,history=history)
    assert "cannot call this debut early, average or late" in assessment["text"]
    assert "not established causes" in assessment["text"]
    assert assessment["profile"]["development_pathway"]["state"]=="established"
    player["development_history"]=history
    player["asset_significance"]=assess_asset_significance(player)
    org=assess_organizational_significance(player,organization="Example Club")
    assert "NCAA" in org["summary"] and "AHL" in org["summary"]
    assert "promotion was delayed" in org["summary"]
    print("PASS: development routing, unrelated news routing, longitudinal observations, baseline uncertainty, organizational significance.")

if __name__=="__main__":run()
