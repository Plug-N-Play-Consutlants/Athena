"""v0.7.10.54.0: provider period rosters -> NHL G+A -> Fantrax totals -> Scout."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile

import pytest

from Athena.Investigation.historical_roster_attribution import (
    acquire_period_rosters, backfill_period_rosters, normalize_period_rosters,
    reconcile_period_points, roster_path,
)
from Athena.Investigation.nhl_period_production import normalize_nhl_period_production
from Scout.conversation.league_recap_narrative import compose_period_report


def _raw(period=3, teams=14):
    return {"period": period, "rosters": {
        f"team{n}": {"teamName": f"Team {n}", "rosterItems": [
            {"id": f"active{n}", "status": "ACTIVE", "position": "C"},
            {"id": f"reserve{n}", "status": "RESERVE", "position": "RW"},
            {"id": f"injured{n}", "status": "INJURED_RESERVE", "position": "D"},
        ]} for n in range(1, teams + 1)
    }}


def _normal(period=3):
    return normalize_period_rosters(_raw(period), league_id="league1", season="2026", period=period,
                                    expected_teams=14, team_ids={f"team{i}" for i in range(1,15)})


def _production(period=3, with_gaps=False):
    records = [{"fantrax_player_id": f"active{i}", "player_name": f"Player {i}",
                "points": i, "goals": 1, "assists": i-1, "games_played": 3}
               for i in range(1,15)]
    records.append({"fantrax_player_id": "reserve1", "player_name": "Reserve One",
                    "points": 20, "goals": 10, "assists": 10, "games_played": 3})
    if with_gaps:
        records = [r for r in records if r["fantrax_player_id"] != "active2"]
    return {"verified": True, "period": period, "records": records,
            "roster_crosswalk_ids": [f"active{i}" for i in range(1, 15) if not (with_gaps and i == 2)]}


def _comparison(mismatch=False):
    return {"status": "compared", "period": 3, "teams": [
        {"team_id": f"team{i}", "name": f"Team {i}",
         "period_points": i + (2 if mismatch and i == 2 else 0)} for i in range(1, 15)
    ]}


def test_realistic_period_rosters_validate_all_fourteen_teams_and_active_reserve():
    parsed = _normal()
    assert parsed["period"] == 3
    assert parsed["team_count"] == 14
    assert parsed["player_count"] == 42
    assert parsed["active_count"] == 14
    assert parsed["records"][0]["owner_team_id"] == "team1"
    assert parsed["records"][0]["active_for_period"] is True
    assert parsed["records"][1]["active_for_period"] is False


@pytest.mark.parametrize("modify", [
    lambda p: p.update(period=4),
    lambda p: p.pop("period"),
    lambda p: p["rosters"].pop("team14"),
    lambda p: p["rosters"]["team14"]["rosterItems"][0].update(id="active1"),
    lambda p: p["rosters"]["team1"]["rosterItems"][0].update(status="UNDECIDED"),
    lambda p: p["rosters"]["team1"].pop("rosterItems"),
    lambda p: p["rosters"]["team1"]["rosterItems"][0].pop("position"),
])
def test_invalid_period_coverage_duplicate_status_and_position_fail_closed(modify):
    payload = _raw()
    modify(payload)
    with pytest.raises(ValueError):
        normalize_period_rosters(payload, league_id="league1", season=2026, period=3, expected_teams=14)


def test_acquisition_backfills_week_1_to_3_and_uses_scoped_cache():
    class Client:
        calls = []
        def __init__(self, **kwargs):
            assert kwargs["league_id"] == "league1"
        def get_team_rosters(self, period):
            self.calls.append(period)
            return _raw(period)
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        now = datetime(2026, 10, 21, tzinfo=timezone.utc)
        result = backfill_period_rosters(league_id="league1", season=2026, through_period=3,
                                         expected_teams=14, output_dir=root,
                                         client_factory=Client, clock=now)
        assert result["status"] == "verified" and result["verified_count"] == 3
        assert Client.calls == [1, 2, 3]
        for number in (1,2,3):
            assert roster_path(root,"league1",2026,number).exists()
        result = backfill_period_rosters(league_id="league1", season=2026, through_period=3,
                                         expected_teams=14, output_dir=root,
                                         client_factory=Client, clock=now + timedelta(minutes=5))
        assert result["status"] == "verified" and Client.calls == [1,2,3]
        assert result["periods"][3]["cached"] is True


def test_wrong_period_from_provider_is_not_archived():
    class Client:
        def __init__(self, **kwargs): pass
        def get_team_rosters(self, period): return _raw(4)
    with tempfile.TemporaryDirectory() as temp:
        result = acquire_period_rosters(league_id="league1", season=2026, period=3,
                                         expected_teams=14, output_dir=Path(temp), client_factory=Client)
        assert not result["verified"] and result["status"] == "unverified_period_roster"
        assert not roster_path(Path(temp), "league1", 2026, 3).exists()


def test_team_by_team_reconciliation_excludes_reserves_and_ir():
    audit = reconcile_period_points(_normal(), _production(), _comparison())
    assert audit["status"] == "reconciled" and audit["fully_reconciled_teams"] == 14
    assert audit["numeric_matched_teams"] == 14
    assert audit["teams"][0]["identified_active_nhl_points"] == 1
    assert audit["teams"][0]["contributors"][0]["name"] == "Player 1"
    assert all(x["player_id"] != "reserve1" for x in audit["teams"][0]["contributors"])


def test_unmatched_player_or_team_delta_blocks_confirmed_credit():
    audit = reconcile_period_points(_normal(), _production(with_gaps=True), _comparison(mismatch=True))
    assert audit["status"] == "partial"
    assert audit["teams"][1]["status"] == "discrepancy"
    assert audit["teams"][1]["difference"] == 4
    assert audit["teams"][1]["unmatched_active_ids"] == ["active2"]


def test_standings_period_must_match_roster_and_nhl_period():
    assert reconcile_period_points(_normal(), _production(period=2), _comparison())["status"] == "wrong_period"


def test_scout_explains_verified_contributors_and_separates_unverified_teams():
    audit = reconcile_period_points(_normal(), _production(), _comparison(mismatch=True))
    report = compose_period_report(research={
        "schema": "athena.league_period_research.v2", "league_name": "JHLPAA", "period": 3,
        "findings": [{"kind": "scoring_leader", "team": "Team 14", "period_points": 14}],
        "comparison": _comparison(mismatch=True),
        "historical_roster_attribution": audit,
        "coverage": {"roster_and_keeper_context": "historical_period_lineup", "fantasy_point_attribution": "partial"},
    })
    assert "Historical lineup scoring" in report
    assert "Team 14:" in report and "Player 14 (14)" in report
    assert "not reconciled" in report
    assert "current snapshot only; not period history" not in report


def test_corrupt_historical_cache_is_refetched_not_trusted():
    class Client:
        calls = 0
        def __init__(self, **kwargs): pass
        def get_team_rosters(self, period):
            Client.calls += 1
            return _raw(period)
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        cache = roster_path(root, "league1", 2026, 3)
        cache.parent.mkdir(parents=True)
        cache.write_text('{"period":3,"verified":true,"records":[]}', encoding="utf-8")
        result = acquire_period_rosters(league_id="league1", season=2026, period=3,
                                         expected_teams=14, output_dir=root, client_factory=Client)
        assert result["verified"] and result["player_count"] == 42
        assert Client.calls == 1


def test_nhl_cache_fingerprint_differs_when_period_roster_replaces_current_snapshot():
    from Athena.Investigation.nhl_period_production import acquire_nhl_period_production
    from Tests.test_points_based_player_reporting_0710530 import _data, _schedule

    class NHL:
        calls = []
        def get_stats(self, endpoint, params):
            self.calls.append("stats")
            return _data()
        def get_web(self, endpoint):
            self.calls.append("schedule")
            return _schedule()[0]

    # Two small rosters represent a player changing owner and ACTIVE status.
    period_roster = {"verified": True, "period": 3, "records": [
        {"player_id": "p1", "owner_team_id": "t1", "owner_team": "Team One", "roster_status": "ACTIVE"},
        {"player_id": "p2", "owner_team_id": "t2", "owner_team": "Team Two", "roster_status": "RESERVE"},
    ]}
    boundary = {"status": "verified_boundary", "boundary_kind": "points_based_roster_period",
                "start_at": "2026-10-12T13:00:00-04:00", "end_at": "2026-10-19T18:59:59-04:00"}
    identity = [{"fantrax_player_id": "p1", "nhl_player_id": "8471", "resolution_status": "resolved", "canonical_player_name": "Alpha"},
                {"fantrax_player_id": "p2", "nhl_player_id": "8472", "resolution_status": "resolved", "canonical_player_name": "Beta"}]
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        (root / "player_identity_map.json").write_text(json.dumps(identity))
        (root / "player_master.json").write_text(json.dumps([{"player_id": "p1", "owner_team": "Old owner"}]))
        clock = datetime(2026, 10, 21, tzinfo=timezone.utc)
        common = dict(league_id="league1", season=2026, period=3, boundary=boundary,
                      client_factory=NHL, output_dir=root, clock=clock)
        current = acquire_nhl_period_production(**common)
        assert current["verified"] and current["roster_basis"] == "current_snapshot_only"
        historical = acquire_nhl_period_production(**common, period_rosters=period_roster)
        assert historical["verified"] and historical["roster_basis"] == "verified_historical_period"
        assert not historical.get("cached") and len(NHL.calls) == 6
        assert historical["records"][0]["current_owner"] == "Team One"
        repeat = acquire_nhl_period_production(**common, period_rosters=period_roster)
        assert repeat.get("cached") and len(NHL.calls) == 6


def test_optional_sync_archives_historical_rosters_and_records_manifest():
    from Athena.Investigation.sync_period_rosters import run
    class Client:
        seen = []
        def __init__(self, **kwargs): pass
        def get_team_rosters(self, period):
            Client.seen.append(period)
            return _raw(period)
    from Tests.test_points_based_player_reporting_0710530 import RAW_POINTS_LEAGUE
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        now = datetime(2026, 10, 21, 12, tzinfo=timezone.utc)
        info = run(league_info=RAW_POINTS_LEAGUE, league_id="league1", season=2026,
                   client_factory=Client, output_dir=root, clock=now)
        assert info["status"] == "verified"
        assert info["selected_period"] == 3 and info["verified_count"] == 3
        assert info["attempted_count"] == 3 and Client.seen == [1,2,3]
        manifest = json.loads((root / "PeriodRosters" / "sync_manifest.json").read_text())
        assert manifest["periods"]["2"]["verified"] is True
        assert roster_path(root,"league1",2026,1).exists()


def test_sync_unverified_history_does_not_claim_success():
    from Athena.Investigation.sync_period_rosters import run
    with tempfile.TemporaryDirectory() as temp:
        info = run(league_info={"scoringSystem": {"type": "POINTS_BASED"}},
                   league_id="league1", season=2026, output_dir=Path(temp),
                   clock=datetime(2026,10,21,tzinfo=timezone.utc))
        assert info["status"] == "unverified" and info["verified_count"] == 0
