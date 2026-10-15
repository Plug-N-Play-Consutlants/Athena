from pathlib import Path
from tempfile import TemporaryDirectory
import json
from Athena.Investigation.recap_context import reconcile_recap_context
from Athena.Investigation.league_recap import investigate_period_stories

with TemporaryDirectory() as d:
    root = Path(d)
    (root / "player_pool_master.json").write_text(json.dumps({"active_season":2026,"fetched_at":"2026-10-14T00:00:00Z","records":[{"fantasy_team":"A","roster_slot":"injured_reserve","player_name":"Player One"}]}))
    (root / "player_production.json").write_text(json.dumps([{"season":20252026,"points":99}]))
    (root / "draft_picks.json").write_text(json.dumps({"season":2026,"future_draft_assets":{"picks":[{"year":2027,"ownership_status":"traded","current_owner":{"team_name":"A"}}]}}))
    result=reconcile_recap_context(root,active_season=2026,selected_period=2,teams=["A"])
    assert result["roster"]["status"] == "current_snapshot_context_only"
    assert not result["roster"]["period_lineup_verified"]
    assert result["injuries"]["teams"]["A"] == ["Player One"]
    assert not result["injuries"]["period_injury_verified"]
    assert not result["production"]["period_production_verified"]
    assert result["draft_assets"]["teams"]["A"][2027] == 1
    assert not result["draft_assets"]["period_trade_link_verified"]
    assert reconcile_recap_context(root,active_season=2025)["roster"]["status"] == "season_unverified"
    stories=investigate_period_stories({"status":"compared","teams":[{"team_id":"1","name":"A","rank":3,"rank_change":-1,"period_points":20},{"team_id":"2","name":"B","rank":1,"rank_change":0,"period_points":41},{"team_id":"3","name":"C","rank":2,"rank_change":0,"period_points":38},{"team_id":"4","name":"D","rank":4,"rank_change":0,"period_points":32}]},None,{},period=2)
    assert any("fell 1 place" in s["text"] for s in stories)
print("Recap context reconciliation regression: PASS")
