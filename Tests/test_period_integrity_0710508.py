from datetime import date
from Athena.Investigation.fantrax_period_calendar import resolve_latest_completed_scoring_period
from Athena.Investigation.period_evidence_acquisition import acquire_player_period_production

class FakeClient:
    payload = None
    def __init__(self, **kwargs): pass
    def has_cookie_auth(self): return True
    def get_player_stats(self, params=None): return self.payload
    def is_error_payload(self, payload): return False

def test_calendar_overlap_is_not_completed():
    result = resolve_latest_completed_scoring_period({"scoringPeriods": [
        {"period": 1, "startDate": "2026-10-01", "endDate": "2026-10-10"},
        {"period": 2, "startDate": "2026-10-10", "endDate": "2026-10-18"}]}, today=date(2026,10,20))
    assert result["status"] == "unverified"

def test_period_player_integrity():
    good = {"season": "2026", "period": 3, "players": [{"playerId": "a", "goals": 2, "assists": 1}]}
    FakeClient.payload = good
    assert acquire_player_period_production(league_id="league", season="2026", period=3, client_factory=FakeClient)["verified"]
    for bad in [
        [{"playerId": "a", "goals": True, "assists": 1}],
        [{"playerId": "a", "goals": float("nan"), "assists": 1}],
        [{"playerId": "a", "goals": 1, "assists": -1}],
        [{"playerId": "a", "goals": 1, "assists": 1}, {"playerId": "a", "goals": 0, "assists": 0}],
        [{"playerId": "a", "goals": 1, "assists": 1, "period": 2}],
    ]:
        FakeClient.payload = {**good, "players": bad}
        assert not acquire_player_period_production(league_id="league", season="2026", period=3, client_factory=FakeClient)["verified"]
