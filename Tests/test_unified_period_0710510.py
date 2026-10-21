from datetime import date
from Athena.Investigation.fantrax_period_calendar import resolve_unified_period
from Athena.Inquiry.execution import summarize_recent_league_activity
from Athena.Investigation.league_editorial import investigate_league_period

PERIODS = [
    {'period': 1, 'startDate': '2026-09-29', 'endDate': '2026-10-04'},
    {'period': 2, 'startDate': '2026-10-05', 'endDate': '2026-10-11'},
    {'period': 3, 'startDate': '2026-10-12', 'endDate': '2026-10-18'},
    {'period': 4, 'startDate': '2026-10-19', 'endDate': '2026-10-25'},
]

def test_matching_schedules_are_one_context():
    r = resolve_unified_period({'data': {'rosterPeriods': PERIODS, 'scoringPeriods': PERIODS}}, today=date(2026,10,21))
    assert (r['status'], r['period'], r['start'], r['end']) == ('calendar_closed', 3, '2026-10-12', '2026-10-18')

def test_roster_schedule_alone_is_valid_shared_period():
    r = resolve_unified_period({'rosterPeriods': PERIODS}, today=date(2026,10,21))
    assert r['period'] == 3

def test_mismatched_schedules_do_not_merge():
    changed = [dict(p) for p in PERIODS]
    changed[0]['startDate'] = '2026-09-30'
    assert resolve_unified_period({'rosterPeriods': PERIODS, 'scoringPeriods': changed})['status'] == 'calendar_conflict'

def test_transactions_and_editorial_share_exact_window():
    rows = {'records': [
        {'transaction_id': 'a', 'timestamp': '2026-10-14T12:00:00Z', 'transaction_type': 'trade', 'summary': 'Trade A'},
        {'transaction_id': 'b', 'timestamp': '2026-10-20T12:00:00Z', 'transaction_type': 'trade', 'summary': 'Trade B'},
        {'transaction_id': 'c', 'period': 3, 'timestamp': '2026-10-20T12:00:00Z', 'transaction_type': 'trade', 'summary': 'Trade C'},
        {'transaction_id': 'd', 'period': 4, 'timestamp': '2026-10-14T12:00:00Z', 'transaction_type': 'trade', 'summary': 'Trade D'},
    ]}
    bounds = {'start': '2026-10-12', 'end': '2026-10-18'}
    result = summarize_recent_league_activity(rows, period=3, period_bounds=bounds)
    editorial = investigate_league_period(rows, 3, period_bounds=bounds)
    assert result['transaction_count'] == editorial['record_count'] == 2
    assert result['scope_method'] == 'period_label_or_shared_bounds'
