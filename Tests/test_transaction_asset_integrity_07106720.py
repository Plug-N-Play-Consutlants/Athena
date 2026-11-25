"""Regression: provider trade assets and separate event/effective period meaning."""
from pathlib import Path
import json

from Providers.Fantrax.build.transaction_master import _records, _group_rows, _normalize_group
from Athena.Investigation.transaction_event_intelligence import investigate_transactions
from Scout.conversation.multi_period_publication import publish_multi_period

ROOT = Path(__file__).resolve().parents[1]


def _observed_trade():
    payload = json.loads((ROOT / 'Tests' / 'fixtures' / 'fantrax_bobby_bubba_pick_trade_2026.json').read_text(encoding='utf-8'))
    group = next(g for g in _group_rows(_records(payload))
                 if g['tx_set_id'] == 'ka1omc9imwjh6rq7')
    return _normalize_group(group, 0)


def _calendar():
    return {'status':'calendar_closed','boundary_kind':'scoring',
            'schedule':{8:{'start':'2026-11-16','end':'2026-11-22'},
                        9:{'start':'2026-11-23','end':'2026-11-29'}}}


def test_raw_pick_is_preserved_with_identity_and_transfer_direction():
    trade = _observed_trade()
    assert trade['transaction_type'] == 'trade'
    assert len(trade['assets']) == 3
    pick = next(a for a in trade['assets'] if a['asset_type'] == 'draft_pick')
    assert pick['draft_pick'] == {'year': 2028, 'round': 3,
                                  'original_team_name': 'Bubba’s Bruisers'}
    assert pick['asset_id'] == ''  # no invented provider-specific pick identifier
    assert pick['provider_reference']['source_field'] == 'draftPickDisplayParts'
    assert pick['movement_context']['from_team_name'] == 'Bubba’s Bruisers'
    assert pick['movement_context']['to_team_name'] == 'Bobby Orr'
    assert len(trade['asset_movements']) == 3


def test_trade_event_and_roster_effective_week_are_distinct():
    trade = _observed_trade()
    assert trade['event_timestamp'].startswith('Mon Nov 16')
    assert trade['roster_effective_period'] == '8'
    output = investigate_transactions({'records':[trade]}, [8], calendar=_calendar())
    event = output['spotlights'][0]
    assert event['event_period'] == 8
    assert event['event_period_source'] == 'provider_calendar_event_date'
    assert event['pick_count'] == 1
    assert event['player_count'] == 2
    assert event['asset_count'] == 3
    assert '2028 Round 3 draft pick' in ' '.join(event['received']['Bobby Orr'])
    assert any(a['asset_type'] == 'draft_pick' and a['draft_pick']['round'] == 3
               for a in event['asset_movements'])


def test_publication_does_not_omit_pick():
    trade = _observed_trade()
    output = investigate_transactions({'records':[trade]}, [8], calendar=_calendar())
    report = publish_multi_period({'status':'verified','periods':[8],
                                   'transactions':output['periods'],
                                   'transaction_spotlights':output['spotlights']})
    assert '2028 Round 3 draft pick' in report
    assert 'Bobby Orr received' in report


def test_missing_pick_payload_does_not_invent_one():
    trade = _observed_trade()
    assert sum(a['asset_type'] == 'draft_pick' for a in trade['assets']) == 1
    payload = json.loads((ROOT / 'Tests' / 'fixtures' / 'fantrax_bobby_bubba_pick_trade_2026.json').read_text(encoding='utf-8'))
    group = next(g for g in _group_rows(_records(payload))
                 if g['tx_set_id'] == 'ka1omc9imwjh6rq7')
    group['rows'] = [r for r in group['rows'] if 'draftPickDisplayParts' not in r]
    reduced = _normalize_group(group, 0)
    assert len(reduced['assets']) == 2
    assert all(a['asset_type'] == 'player' for a in reduced['assets'])
