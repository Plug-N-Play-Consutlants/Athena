"""Offline contract checks: no network access, no fabricated period evidence."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Athena.Investigation.period_evidence_acquisition import acquire_player_period_production as acquire

class Fake:
    def __init__(self, *, league_id, season): self.season=season
    def get_optional_endpoint(self, name, default): return "configured/player_stats"
    def has_cookie_auth(self): return True
    def is_error_payload(self, payload): return bool(isinstance(payload,dict) and payload.get("error"))
    def get_player_stats(self, params=None):
        return {"season":"2026", "period":2, "players":[{"player_id":"p1", "goals":2, "assists":1}]}

assert acquire(league_id="L",season="2026",period=2,client_factory=Fake)["verified"]
class Wrong(Fake):
    def get_player_stats(self, **kwargs): return {"season":"2026", "period":1, "players":[{"player_id":"p1", "goals":2,"assists":1}]}
assert acquire(league_id="L",season="2026",period=2,client_factory=Wrong)["status"] == "unverified_period"
class Failure(Fake):
    def get_player_stats(self, **kwargs): raise ConnectionError("simulated")
assert acquire(league_id="L",season="2026",period=2,client_factory=Failure)["status"] == "failed"
class NoEndpoint(Fake):
    def get_optional_endpoint(self, name, default): return ""
assert acquire(league_id="L",season="2026",period=2,client_factory=NoEndpoint)["attempted"]
class Ambiguous(Fake):
    def get_player_stats(self, **kwargs): return [{"player_id":"p1", "goals":2,"assists":1}]
assert acquire(league_id="L",season="2026",period=2,client_factory=Ambiguous)["status"] == "unverified_source"
assert acquire(league_id="L",season="2026",period=None,client_factory=Fake)["status"] == "not_attempted"
print("[PASS] Player production acquisition lifecycle and temporal validation")

class ProviderError(Fake):
    def get_player_stats(self, **kwargs):
        return {"error": {"code": "UNSUPPORTED_METHOD", "message": "Unknown endpoint"}}
result = acquire(league_id="L", season="2026", period=2, client_factory=ProviderError)
assert result["status"] == "source_error"
assert result["diagnostic"] == {"code": "UNSUPPORTED_METHOD", "message": "Unknown endpoint"}
class SecretError(Fake):
    def get_player_stats(self, **kwargs):
        return {"error": {"code": "NO", "message": "token=abcdef https://host.invalid/path?token=secret"}}
result = acquire(league_id="L", season="2026", period=2, client_factory=SecretError)
assert "abcdef" not in str(result) and "secret" not in str(result)
