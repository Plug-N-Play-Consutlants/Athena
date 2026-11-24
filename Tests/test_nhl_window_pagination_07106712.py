"""NHL historical game data pagination and fail-closed source coverage."""
from __future__ import annotations

import pytest
from Athena.Investigation.nhl_period_production import fetch_complete_nhl_game_summary


def _rows(n):
    return [{'gameId': 1000+i//20, 'playerId': 8000000+i} for i in range(n)]


class Client:
    def __init__(self, rows, *, initial_size=None, broken=None, page_cap=None):
        self.rows = rows
        self.initial_size = initial_size
        self.broken = broken
        self.page_cap = page_cap
        self.requests = []

    def get_stats(self, endpoint, params):
        assert endpoint == 'skater/summary'
        self.requests.append(params)
        if params['limit'] == -1:
            size = self.initial_size if self.initial_size is not None else len(self.rows)
            return {'total':len(self.rows), 'data':self.rows[:size]}
        if self.broken == 'changing_total':
            return {'total':len(self.rows)+1, 'data':self.rows[params['start']:params['start']+params['limit']]}
        if self.broken == 'short_page' and params['start'] > 0:
            return {'total':len(self.rows), 'data':[]}
        if self.broken == 'duplicate_page' and params['start'] > 0:
            return {'total':len(self.rows), 'data':self.rows[:params['limit']]}
        effective = min(params['limit'], self.page_cap) if self.page_cap else params['limit']
        return {'total':len(self.rows), 'data':self.rows[params['start']:params['start']+effective]}


def test_complete_single_response_does_not_paginate():
    c=Client(_rows(20))
    assert len(fetch_complete_nhl_game_summary(c,'seasonId=20262027')['data'])==20
    assert len(c.requests)==1


def test_truncated_limit_minus_one_retrieves_all_pages():
    c=Client(_rows(1101), initial_size=100)
    data=fetch_complete_nhl_game_summary(c,'seasonId=20262027')
    assert len(data['data'])==1101
    assert [r['start'] for r in c.requests]==[0,0,500,1000]
    assert [r['limit'] for r in c.requests]==[-1,500,500,101]


@pytest.mark.parametrize('broken', ['changing_total','short_page','duplicate_page'])
def test_bad_pagination_is_never_accepted(broken):
    c=Client(_rows(1101), initial_size=100, broken=broken)
    with pytest.raises(ValueError):
        fetch_complete_nhl_game_summary(c,'seasonId=20262027')


def test_empty_source_is_not_equivalent_to_a_zero_point_period():
    c=Client([])
    with pytest.raises(ValueError,match='zero rows'):
        fetch_complete_nhl_game_summary(c,'seasonId=20262027')


def test_unbounded_source_is_refused():
    c=Client(_rows(1001), initial_size=100)
    with pytest.raises(ValueError,match='bounded'):
        fetch_complete_nhl_game_summary(c,'seasonId=20262027',max_rows=1000)


def test_server_caps_each_page_below_requested_size_without_losing_rows():
    c = Client(_rows(1101), initial_size=100, page_cap=100)
    result = fetch_complete_nhl_game_summary(c, 'seasonId=20262027')
    assert len(result['data']) == 1101
    assert [p['start'] for p in c.requests] == [0] + list(range(0, 1101, 100))
    assert c.requests[-1]['limit'] == 1


def test_server_caps_pages_to_unusually_small_chunks_but_still_completes():
    c = Client(_rows(251), initial_size=50, page_cap=23)
    result = fetch_complete_nhl_game_summary(c, 'seasonId=20262027')
    assert len(result['data']) == 251
    assert c.requests[2]['start'] == 23
    assert c.requests[-1]['start'] == 230


def test_every_nhl_page_uses_stable_game_and_player_sort():
    import json
    c = Client(_rows(201), initial_size=100, page_cap=100)
    result = fetch_complete_nhl_game_summary(c, 'seasonId=20262027')
    assert len(result['data']) == 201
    for request in c.requests:
        assert json.loads(request['sort']) == [
            {'property': 'gameId', 'direction': 'ASC'},
            {'property': 'playerId', 'direction': 'ASC'},
        ]


class UnstableWithoutSort:
    def __init__(self):
        self.rows = _rows(250)

    def get_stats(self, endpoint, params):
        if params['limit'] == -1:
            return {'total': 250, 'data': self.rows[:100]}
        # Emulate a backend that changes tie ordering if the sort is omitted.
        import json
        sort = json.loads(params.get('sort', '[]'))
        if sort != [{'property':'gameId','direction':'ASC'},
                    {'property':'playerId','direction':'ASC'}]:
            return {'total':250,'data': self.rows[max(0,params['start']-25):][:100]}
        return {'total': 250, 'data': self.rows[params['start']:params['start']+min(params['limit'],100)]}


def test_explicit_unique_sort_prevents_overlap_from_unstable_default_order():
    rows = fetch_complete_nhl_game_summary(UnstableWithoutSort(), 'seasonId=20262027')['data']
    assert len(rows) == 250
    assert len({(row['playerId'],row['gameId']) for row in rows}) == 250


class IgnoresOffset:
    def get_stats(self, endpoint, params):
        rows = _rows(150)
        return {'total':150,'data':rows[:100]}


def test_stable_sort_does_not_override_provider_offset_failure():
    with pytest.raises(ValueError, match='overlapping|invalid page'):
        fetch_complete_nhl_game_summary(IgnoresOffset(), 'seasonId=20262027')
