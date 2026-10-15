"""Contract regression: one fxpa player-stats operation, no invalid fxea route."""
from pathlib import Path
import sys, ast, json
base=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(base))
from Athena.Investigation.period_evidence_acquisition import acquire_player_period_production
class FakeClient:
    def __init__(self, **kwargs): self.calls=0
    def has_cookie_auth(self): return True
    def get_player_stats(self):
        self.calls+=1
        return {"players":[{"playerId":"x","goals":3,"assists":2}]}
    def is_error_payload(self,p):return False
result=acquire_player_period_production(league_id="league",season=2026,period=2,client_factory=FakeClient)
assert result["attempted"] and not result["verified"] and result["status"]=="unverified_period",result
source=(base/'Providers/Fantrax/fantrax_client.py').read_text()
assert '"method": "getPlayerStats"' in source
assert 'return self.fxpa_request({"method": "getPlayerStats", "data": data})' in source
config=json.loads((base/'Configuration/config.json').read_text())
assert 'player_stats' not in config['provider']['endpoints']
print('[PASS] fxpa player stats routed through provider; no fabricated period verification')
