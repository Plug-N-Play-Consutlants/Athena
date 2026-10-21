"""Regression: verified calendar evidence must reach Scout's editorial response."""
from pathlib import Path

def test_period_calendar_propagation():
    root = Path(__file__).resolve().parents[1]
    execution = (root / 'Athena/Investigation/period_execution.py').read_text(encoding='utf-8')
    router = (root / 'Scout/conversation/router.py').read_text(encoding='utf-8')
    assert '"period_calendar": period_calendar' in execution
    assert 'calendar_boundary_verified' in execution
    assert 'calendar = execution.get("period_calendar")' in router
    assert 'calendar dates alone do not establish finalized scoring results' in router

def test_unified_calendar_accepts_one_schedule_and_rejects_conflicts():
    from Athena.Investigation.fantrax_period_calendar import resolve_unified_period
    schedule = [{'period': 2, 'startDate': '2026-10-05', 'endDate': '2026-10-12'}]
    from datetime import date
    got = resolve_unified_period({'rosterPeriods': schedule}, today=date(2026,10,19))
    assert got['status'] == 'calendar_closed'
    assert got['start'] == '2026-10-05'
    conflict = resolve_unified_period({'rosterPeriods': schedule, 'scoringPeriods': [
        {'period': 2, 'startDate': '2026-10-06', 'endDate': '2026-10-13'}]}, today=date(2026,10,19))
    assert conflict['status'] == 'calendar_conflict'
