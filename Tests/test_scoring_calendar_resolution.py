import unittest
from datetime import date
from Athena.Investigation.fantrax_period_calendar import resolve_latest_completed_scoring_period, parse_period_calendar

class CalendarResolutionTests(unittest.TestCase):
    def test_completed_period_not_current(self):
        payload = {'data': {'scoringPeriods': [
            {'period': 1, 'startDate': '2026-09-29', 'endDate': '2026-10-04'},
            {'period': 2, 'startDate': '2026-10-05', 'endDate': '2026-10-11'},
            {'period': 3, 'startDate': '2026-10-12', 'endDate': '2026-10-18'},
            {'period': 4, 'startDate': '2026-10-19', 'endDate': '2026-10-25'}]}}
        result = resolve_latest_completed_scoring_period(payload, today=date(2026, 10, 20))
        self.assertEqual(result['period'], 3)
        self.assertEqual(result['status'], 'calendar_closed')
    def test_roster_periods_not_scoring_periods(self):
        payload = {'data': {'rosterPeriods': [{'period': 3, 'startDate': '2026-10-12', 'endDate': '2026-10-18'}]}}
        self.assertEqual(resolve_latest_completed_scoring_period(payload, today=date(2026, 10, 20))['status'], 'unverified')
        self.assertEqual(parse_period_calendar(payload, 3)['status'], 'unverified')
    def test_duplicate_periods_fail_closed(self):
        payload = {'scoringPeriods': [{'period': 3}, {'period': 3}]}
        self.assertEqual(resolve_latest_completed_scoring_period(payload)['status'], 'unverified')

if __name__ == '__main__':
    unittest.main()
