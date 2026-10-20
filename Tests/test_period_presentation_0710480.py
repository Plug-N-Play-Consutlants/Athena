"""Regression: verified calendar evidence must reach Scout's editorial response."""
from pathlib import Path

def test_period_calendar_propagation():
    root = Path(__file__).resolve().parents[1]
    execution = (root / 'Athena/Investigation/period_execution.py').read_text(encoding='utf-8')
    router = (root / 'Scout/conversation/router.py').read_text(encoding='utf-8')
    assert '"period_calendar": period_calendar' in execution
    assert 'calendar_boundary_verified' in execution
    assert 'calendar = execution.get("period_calendar")' in router
    assert 'Roster-period dates have not been verified as scoring-period dates.' in router
    assert 'The calendar alone does not establish finalized standings' in router

def test_calendar_scoring_roster_distinction():
    from Athena.Investigation.fantrax_period_calendar import parse_period_calendar
    payload = {'data': {'rosterPeriods': [{'period': 2, 'startDate': '2026-10-05', 'endDate': '2026-10-12'}]}}
    from datetime import date
    got = parse_period_calendar(payload, 2, today=date(2026,10,19))
    assert got['status'] == 'verified_boundary'
    assert got['source'].endswith('.rosterPeriods')
    assert got['completed'] is True
    payload['data']['scoringPeriods'] = [{'period': 2, 'startDate': '2026-10-06', 'endDate': '2026-10-13'}]
    got = parse_period_calendar(payload, 2, today=date(2026,10,19))
    assert got['source'].endswith('.scoringPeriods')
    assert got['start'] == '2026-10-06'
