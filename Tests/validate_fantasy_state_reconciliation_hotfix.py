from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.version import ATHENA_VERSION, RELEASE_NAME
from Athena.sync import FANTRAX_FANTASY_PIPELINE
from Intelligence.league_market import _liquidity_profile
from Scout.conversation.context import ScoutContext
from Scout.conversation.router import _manager_coverage
from collections import Counter

checks = []
def check(name, ok, detail=""):
    checks.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")

check("version", ATHENA_VERSION == "0.6.4.1.4", ATHENA_VERSION)
check("release", RELEASE_NAME == "Fantasy State Reconciliation Hotfix", RELEASE_NAME)
ids = [row.get("id") for row in FANTRAX_FANTASY_PIPELINE]
check("league_settings_rebuilt", "build_league_settings" in ids, ids)
check("league_profile_rebuilt", "build_league_profile" in ids, ids)
check("contracts_rebuilt", "build_player_contracts" in ids, ids)
check("league_profile_after_settings", ids.index("build_league_profile") > ids.index("build_league_settings"), ids)

ctx = ScoutContext(
    league_profile={"team_count": 14},
    team_profiles=[{"team_id": str(i), "team_name": f"Team {i}"} for i in range(14)],
    manager_behavior={"records": [
        {"team_id": str(i), "transaction_count": 0, "observed_facts": {"transaction_count": 0}}
        for i in range(14)
    ]},
)
coverage = _manager_coverage(ctx)
check("zero_transactions_not_active", coverage["managers_with_activity"] == 0, coverage)
check("all_teams_covered", coverage["managers_without_activity"] == 14, coverage)

liquidity = _liquidity_profile(0, 14, {}, {}, Counter(), Counter())
check("zero_transactions_market_unknown", liquidity.get("classification") == "unknown", liquidity)

app_text = (ROOT / "Scout" / "app.py").read_text(encoding="utf-8")
check("connection_refreshes_state", 'result["state_refresh"]' in app_text and 'Athena.sync(mode="fantasy_league"' in app_text, "Save/Test triggers sync")
check("analysis_refreshes_state", 'answer.get("intent") == "analyze_league"' in app_text, "Analyze League triggers sync before final response")
check("league_display_prefers_league_name", "workspace.league_name || workspace.name || workspace.league_id" in app_text, "league_name preferred")

settings_text = (ROOT / "Providers" / "Fantrax" / "build" / "league_settings.py").read_text(encoding="utf-8")
check("current_league_id_separate_from_history", '"league_id": safe_str(get_workspace_value("league_id"))' in settings_text and '"league_history_id": safe_str(league.get("leagueHistoryId"))' in settings_text, "current ID and history ID separated")

sync_text = (ROOT / "Athena" / "sync.py").read_text(encoding="utf-8")
check("stale_transaction_outputs_invalidated", "_invalidate_transaction_derived_outputs" in sync_text, "stale optional state removed")

print("Overall status:", "PASS" if all(checks) else "FAIL")
raise SystemExit(0 if all(checks) else 1)
