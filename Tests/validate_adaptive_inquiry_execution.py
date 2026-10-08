from __future__ import annotations
import sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from Core.version import ATHENA_VERSION
from Athena.Inquiry.execution import construct_transaction_paths, summarize_recent_league_activity
from Knowledge.Intelligence.Public.player_evidence import _target_season_id

fail=[]
def check(name, ok, detail=""):
    print(("PASS" if ok else "FAIL")+f" | {name}"+(f" | {detail}" if detail else ""))
    if not ok: fail.append(name)

check("version", tuple(map(int, ATHENA_VERSION.split("."))) >= (0, 7, 7, 3, 4), ATHENA_VERSION)
check("current NHL season target", _target_season_id()=="20262027", _target_season_id())
construction=construct_transaction_paths(team_name="Toronto Maple Leafs",target_name="Connor McDavid",protected_assets=["Auston Matthews"],cap_waived=True)
check("construction executes", len(construction["paths"])>=3, str(construction["paths"]))
check("protected asset persists", construction["protected_assets"]==["Auston Matthews"], str(construction["protected_assets"]))
check("waived cap changes analysis", "acquisition value" in construction["conclusion"].lower(), construction["conclusion"])
fixture={"records":[
 {"transaction_id":"old","timestamp":"2026-09-20T12:00:00+00:00","transaction_type":"claim_drop","summary":"old move","participants":[{"team_name":"Old"}],"assets":[]},
 {"transaction_id":"trade","timestamp":"2026-10-05T20:46:00+00:00","transaction_type":"trade","summary":"major trade","participants":[{"team_name":"A"},{"team_name":"B"}],"assets":[{"asset_type":"player","asset_name":"Star A"},{"asset_type":"player","asset_name":"Star B"},{"asset_type":"draft_pick","asset_name":"2027 R1"}]},
 {"transaction_id":"fa","timestamp":"2026-10-02T12:00:00+00:00","transaction_type":"claim_drop","summary":"free-agent move","participants":[{"team_name":"C"}],"assets":[{"asset_type":"player","asset_name":"Player C"}]}
]}
activity=summarize_recent_league_activity(fixture,days=7,now=datetime(2026,10,5,21,0,tzinfo=timezone.utc))
check("weekly filter excludes old", activity["transaction_count"]==2, str(activity))
check("trade significance first", activity["highlights"] and activity["highlights"][0]["transaction_id"]=="trade", str(activity["highlights"]))
if fail: raise SystemExit("FAILED: "+", ".join(fail))
