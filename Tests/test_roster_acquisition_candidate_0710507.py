from datetime import date
from Athena.Investigation.fantrax_period_calendar import resolve_roster_period_acquisition_candidate, resolve_latest_completed_scoring_period

def test_roster_calendar_only_nominates_acquisition():
    payload = {"data":{"rosterPeriods":[
        {"period":2,"startDate":"2026-10-05","endDate":"2026-10-11"},
        {"period":3,"startDate":"2026-10-12","endDate":"2026-10-18"},
        {"period":4,"startDate":"2026-10-19","endDate":"2026-10-25"}]}}
    candidate = resolve_roster_period_acquisition_candidate(payload,today=date(2026,10,20))
    assert candidate["period"] == 3
    assert candidate["status"] == "acquisition_candidate"
    assert resolve_latest_completed_scoring_period(payload,today=date(2026,10,20))["status"] == "unverified"

def test_malformed_roster_calendar_cannot_select():
    payload = {"rosterPeriods":[{"period":3,"startDate":"2026-10-12","endDate":"2026-10-18"},
                                {"period":3,"startDate":"2026-10-12","endDate":"2026-10-18"}]}
    assert resolve_roster_period_acquisition_candidate(payload)["status"] == "unverified"
