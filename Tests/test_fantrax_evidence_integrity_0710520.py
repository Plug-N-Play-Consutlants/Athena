from datetime import date
from Athena.Investigation.fantrax_period_calendar import resolve_unified_period


def test_real_roster_calendar_is_not_misrepresented_as_scoring_calendar():
    raw = {"rosterPeriods": [
        {"number": 2, "startDate": "2026-10-05T19:00:00.0-0400", "endDate": "2026-10-12T12:59:59.0-0400"},
        {"number": 3, "startDate": "2026-10-12T13:00:00.0-0400", "endDate": "2026-10-19T18:59:59.0-0400"},
        {"number": 4, "startDate": "2026-10-19T19:00:00.0-0400", "endDate": "2026-10-26T18:59:59.0-0400"},
    ]}
    result = resolve_unified_period(raw, today=date(2026, 10, 21))
    assert result["status"] == "calendar_closed"
    assert result["period"] == 3
    assert result["boundary_kind"] == "roster_only"
    assert result["schedule"][3]["end_at"].startswith("2026-10-19T18:59:59")
    assert "scoring boundaries" in result["reason"]


def test_precise_close_not_midnight_date_projection():
    row = {"number": 3, "startDate": "2026-10-12T13:00:00-04:00", "endDate": "2026-10-19T18:59:59-04:00"}
    assert resolve_unified_period({"rosterPeriods": [row]}, today=date(2026, 10, 19))["period"] is None
    assert resolve_unified_period({"rosterPeriods": [row]}, today=date(2026, 10, 21))["period"] == 3


def test_conflicting_schedules_remain_rejected():
    a = [{"number": 3, "startDate": "2026-10-12", "endDate": "2026-10-18"}]
    b = [{"number": 3, "startDate": "2026-10-12", "endDate": "2026-10-19"}]
    assert resolve_unified_period({"rosterPeriods": a, "scoringPeriods": b})["status"] == "calendar_conflict"
