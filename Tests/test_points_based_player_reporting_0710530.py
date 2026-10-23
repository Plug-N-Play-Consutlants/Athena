"""Consolidated acceptance: POINTS_BASED calendar + NHL game evidence + Scout."""
from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from Athena.Investigation.fantrax_period_calendar import resolve_unified_period
from Athena.Investigation.nhl_period_production import (
    normalize_nhl_period_production, acquire_nhl_period_production,
)
from Scout.conversation.league_recap_narrative import compose_period_report


RAW_POINTS_LEAGUE = {
    "scoringSystem": {"type": "POINTS_BASED"},
    "rosterPeriods": [
        {"number": 2, "startDate": "2026-10-05T19:00:00.0-0400", "endDate": "2026-10-12T12:59:59.0-0400"},
        {"number": 3, "startDate": "2026-10-12T13:00:00.0-0400", "endDate": "2026-10-19T18:59:59.0-0400"},
        {"number": 4, "startDate": "2026-10-19T19:00:00.0-0400", "endDate": "2026-10-26T18:59:59.0-0400"},
    ],
}

def test_points_based_roster_reporting_calendar_resolves_exact_provider_instants():
    r = resolve_unified_period(RAW_POINTS_LEAGUE, today=date(2026,10,21))
    assert r["status"] == "calendar_closed" and r["period"] == 3
    assert r["boundary_kind"] == "points_based_roster_period"
    assert r["scoring_system_type"] == "POINTS_BASED"
    assert r["schedule"][3]["end_at"].startswith("2026-10-19T18:59:59")
    assert "head-to-head" not in r["reason"]


def test_unknown_format_remains_unverified_roster_semantics():
    r = resolve_unified_period({"rosterPeriods": RAW_POINTS_LEAGUE["rosterPeriods"]}, today=date(2026,10,21))
    assert r["boundary_kind"] == "roster_only"


def _data():
    return {
        "total": 4,
        "data": [
            {"playerId": 8471, "gameId": 1001, "gameDate": "2026-10-12", "goals": 1, "assists": 2, "points": 3},
            {"playerId": 8471, "gameId": 1002, "gameDate": "2026-10-15", "goals": 0, "assists": 1, "points": 1},
            {"playerId": 8471, "gameId": 1003, "gameDate": "2026-10-19", "goals": 3, "assists": 0, "points": 3},
            {"playerId": 8472, "gameId": 1004, "gameDate": "2026-10-19", "goals": 1, "assists": 0, "points": 1},
        ],
    }


def _schedule():
    return [{"gameWeek": [{"games": [
        {"id": 1001, "startTimeUTC": "2026-10-12T18:00:00Z"},
        {"id": 1003, "startTimeUTC": "2026-10-19T23:00:00Z"},
        {"id": 1004, "startTimeUTC": "2026-10-19T20:00:00Z"},
    ]}]}]


def _params():
    return dict(league_id="jhlpaa1", season=2026, period=3,
                start_at="2026-10-12T13:00:00-04:00", end_at="2026-10-19T18:59:59-04:00",
                identity_rows=[{"fantrax_player_id": "p1", "nhl_player_id": "8471", "canonical_player_name": "Alpha Player", "resolution_status": "resolved"},
                               {"fantrax_player_id": "p2", "nhl_player_id": "8472", "canonical_player_name": "Beta Player", "resolution_status": "resolved"}],
                roster_rows=[{"player_id": "p1", "player_name": "Alpha Player", "owner_team": "Team Alpha"},
                             {"player_id": "p2", "player_name": "Beta Player", "owner_team": "Team Beta"}])


def test_boundary_game_start_is_verified_and_no_next_period_leakage():
    result = normalize_nhl_period_production(_data(), _schedule(), **_params())
    assert result["status"] == "verified_nhl_window"
    assert result["records"][0]["points"] == 4
    assert result["records"][0]["goals"] == 1
    assert result["records"][0]["assists"] == 3
    assert result["records"][0]["owner_attribution"] == "current_roster_snapshot_only_not_period_eligibility"
    assert result["records"][1]["points"] == 1
    assert result["game_count"] == 3


def test_unverified_boundary_game_rejects_entire_collection():
    try:
        normalize_nhl_period_production(_data(), [{"gameWeek": [{"games": []}]}], **_params())
    except ValueError as exc:
        assert "Boundary-day" in str(exc)
    else:
        raise AssertionError("boundary game without schedule was accepted")


def test_paginated_or_duplicate_or_out_of_window_stats_rejected():
    for payload in ({**_data(), "total": 5},
                    {"total": 2, "data": [_data()["data"][0]] * 2},
                    {"total": 1, "data": [{**_data()["data"][0], "gameDate": "2026-10-25"}]}):
        try:
            normalize_nhl_period_production(payload, _schedule(), **_params())
        except ValueError:
            pass
        else:
            raise AssertionError("incomplete or contradictory stats accepted")


def test_nhl_source_cached_and_scoped_to_exact_window():
    class Client:
        requests = []
        def get_stats(self, endpoint, params):
            self.requests.append((endpoint, params))
            return _data()
        def get_web(self, endpoint):
            self.requests.append((endpoint, None))
            return _schedule()[0]
    boundary = {"status": "verified_boundary", "boundary_kind": "points_based_roster_period",
                "start_at": _params()["start_at"], "end_at": _params()["end_at"]}
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        (base / "player_identity_map.json").write_text(json.dumps(_params()["identity_rows"]))
        (base / "player_master.json").write_text(json.dumps(_params()["roster_rows"]))
        at = datetime(2026,10,21,12,tzinfo=timezone.utc)
        first = acquire_nhl_period_production(league_id="jhlpaa1", season=2026,
                     period=3, boundary=boundary, client_factory=Client,
                     output_dir=base, clock=at)
        assert first["verified"] and len(Client.requests) == 3
        second = acquire_nhl_period_production(league_id="jhlpaa1", season=2026,
                     period=3, boundary=boundary, client_factory=Client,
                     output_dir=base, clock=at)
        assert second["cached"] and len(Client.requests) == 3
        assert "gameDate" in Client.requests[0][1]["cayenneExp"]
        assert "seasonId=20262027" in Client.requests[0][1]["cayenneExp"]


def test_scout_displays_real_nhl_performances_without_claiming_fantasy_credit():
    report = compose_period_report(research={
        "schema": "athena.league_period_research.v2", "league_name": "JHLPAA", "period": 3,
        "findings": [{"kind": "scoring_leader", "team": "Alpha", "period_points": 40}],
        "nhl_player_leaders": [{"player_name": "Alpha Player", "points": 4, "goals": 1,
                                "assists": 3, "games_played": 2}],
        "coverage": {"player_period_production": "verified_nhl_window_only"},
    })
    assert "Individual NHL performances" in report
    assert "Alpha Player: 4 NHL points (1 G, 3 A)" in report
    assert "NOT confirmed fantasy points" in report
    assert "Trading-block change history" not in report
