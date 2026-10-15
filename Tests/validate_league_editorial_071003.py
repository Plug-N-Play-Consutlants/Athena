"""Regression for evidence-backed Week 2 editorial investigation."""
from pathlib import Path
import sys, json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from Athena.Investigation.league_editorial import investigate_league_period
p=Path(__file__).resolve().parents[1]/"Output"/"transaction_history.json"
data=json.loads(p.read_text(encoding="utf-8"))
result=investigate_league_period(data,"2")
assert result["trade_count"] == 2
assert result["record_count"] == 14
assert ("Protect Hronek",2) in result["multiple_trade_teams"]
assert any("Leon Draisaitl" in story["lead"] and "Grabner By the Jussi received" in story["lead"] for story in result["trades"])
assert any("Quinn Hughes" in story["lead"] and "Leeeroy Jenkins received" in story["lead"] for story in result["trades"])
assert len(result["missing_evidence"]) == 3
print("PASS: Week 2 editorial lead, two full trade directions, and bounded evidence gaps")
