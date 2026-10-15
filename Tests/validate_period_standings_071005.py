"""Isolated regression for period selection, comparisons and provider routing."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Athena.Investigation.period_standings import required_periods, compare_periods, acquire_periods
from Providers.Fantrax.fantrax_client import FantraxClient

def run():
    assert required_periods(2) == [1, 2]
    assert required_periods(4, season_to_date=True) == [1, 2, 3, 4]
    one = {"period": 1, "teams": [{"team_id": "a", "name": "A", "rank": 2, "points": 10}, {"team_id": "b", "name": "B", "rank": 1, "points": 15}]}
    two = {"period": 2, "teams": [{"team_id": "a", "name": "A", "rank": 1, "points": 22}, {"team_id": "b", "name": "B", "rank": 2, "points": 18}]}
    output = compare_periods([one, two], requested_period=2)
    assert output["teams"][0]["rank_change"] == 1
    assert output["teams"][0]["period_points"] == 12
    assert compare_periods([two], requested_period=2)["teams"][0]["period_points"] is None
    assert acquire_periods(2, lambda p: {1: one, 2: two}[p])["status"] == "compared"
    client = object.__new__(FantraxClient)
    client.fxpa_request = lambda request: request
    assert client.get_standings(2)["data"]["period"] == 2
    assert client.get_standings(2, only_period=True)["data"]["timeStartType"] == "PERIOD_ONLY"
    print("PASS: period standings acquisition contract and temporal comparisons")

if __name__ == "__main__": run()
