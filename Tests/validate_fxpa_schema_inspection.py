"""No sensitive provider values may leak into schema inspection."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from Athena.Investigation.period_evidence_acquisition import inspect_player_stats_schema, acquire_player_period_production
private = {"token":"SECRET", "playerName":"Alice", "leagueId":"PRIVATE", "statsTable":[{"playerId":"SENSITIVE"}], "tableHeader":{"cells":[{"label":"G"},{"label":"A"},{"label":"PRIVATE SECRET"}]}, "seasonOrProjections":[{"name":"PRIVATE"}]}
shape=inspect_player_stats_schema(private)
assert shape["recognized_stat_headers"] == ["A", "G"]
assert shape["statsTable_count"] == 1
assert all(x not in str(shape) for x in ("SECRET", "Alice", "PRIVATE", "SENSITIVE")),shape
class Fake:
 def __init__(self,**kwargs):pass
 def has_cookie_auth(self):return True
 def get_player_stats(self):return private
 def is_error_payload(self,p):return False
result=acquire_player_period_production(league_id="L",season=2026,period=2,client_factory=Fake)
assert result["status"] == "unverified_period" and result["schema_inspection"] == shape
print("[PASS] schema inspection is bounded, sanitized and does not fabricate period attribution")
