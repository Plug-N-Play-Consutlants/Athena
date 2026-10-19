"""Deterministic JHLPAA timeline regression; no live provider required."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from Athena.Investigation.period_timeline import PeriodWindow, TradeTiming, earliest_lock


def run():
    east = ZoneInfo('America/Toronto')
    west = ZoneInfo('America/Vancouver')
    monday = datetime(2026, 10, 19, 19, tzinfo=east)
    current = earliest_lock('week3', [monday, monday + timedelta(hours=3)])
    assert current.lock_at == datetime(2026, 10, 19, 18, 55, tzinfo=east).astimezone(timezone.utc)
    assert current.lock_at.astimezone(west).hour == 15
    next_game = datetime(2026, 10, 27, 12, tzinfo=east)  # no Monday games
    next_week = earliest_lock('week4', [next_game])
    assert next_week.lock_at.astimezone(east).hour == 11
    current = PeriodWindow('week3', monday, effective_end=datetime(2026, 10, 26, 0, tzinfo=east))
    wednesday = datetime(2026, 10, 21, 14, tzinfo=east)
    trade = lambda at: TradeTiming(at, 'seller', 'buyer', current, next_week).resolve()
    assert trade(wednesday)['scoring_team'] == 'seller'
    assert trade(wednesday)['eligible_from'] == 'week4'
    assert trade(datetime(2026, 10, 26, 10, tzinfo=east))['phase'] == 'grey_zone'
    assert trade(datetime(2026, 10, 26, 10, tzinfo=east))['scoring_team'] is None
    assert trade(datetime(2026, 10, 19, 18, 54, tzinfo=east))['scoring_team'] == 'buyer'
    assert trade(datetime(2026, 10, 27, 12, tzinfo=east))['eligible_from'] is None
    try:
        earliest_lock('week', [])
    except ValueError:
        pass
    else:
        raise AssertionError('Missing game schedule must not fabricate a lock')
    try:
        PeriodWindow('week', datetime(2026, 10, 19, 19)).lock_at
    except ValueError:
        pass
    else:
        raise AssertionError('Naive timestamps must be rejected')
    print('period timeline regression PASS')


if __name__ == '__main__':
    run()
