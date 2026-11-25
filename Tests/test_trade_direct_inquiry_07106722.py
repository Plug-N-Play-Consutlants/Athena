"""Direct trade inquiry must resolve provider names, event dates and typed assets."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

from Athena.Inquiry.execution import reconstruct_league_trade
from Providers.Fantrax.build.transaction_master import _group_rows, _normalize_group, _records
from Scout.conversation.router import _fantasy_trade_investigation

ROOT = Path(__file__).resolve().parents[1]


def _history():
    payload = json.loads((ROOT / 'Tests' / 'fixtures' / 'fantrax_bobby_bubba_pick_trade_2026.json').read_text(encoding='utf-8'))
    current = _normalize_group(next(g for g in _group_rows(_records(payload)) if g['tx_set_id'] == 'ka1omc9imwjh6rq7'), 0)
    previous = copy.deepcopy(current)
    previous['transaction_id'] = 'older-trade'
    previous['timestamp'] = previous['event_timestamp'] = 'Mon Oct 26, 2026, 4:38PM'
    previous['assets'] = [{'asset_name':'Unrelated Player', 'asset_type':'player'}]
    return {'records': [previous, current]}


def test_date_filters_same_pair_of_participants():
    history = _history()
    result = reconstruct_league_trade(history, team_names=['Bobby Orr', "Bubba's Bruisers"], date_hint='November 16')
    assert result['matched_count'] == 1
    assert result['matches'][0]['record']['transaction_id'] != 'older-trade'
    assert reconstruct_league_trade(history, team_names=['Bobby Orr', "Bubba's Bruisers"], date_hint='November 17')['matched_count'] == 0


def test_direct_scout_question_matches_canonical_teams_and_pick():
    answer = _fantasy_trade_investigation(
        SimpleNamespace(transaction_history=_history()),
        "Tell me about the November 16 trade between Bobby Orr and Bubba's Bruisers in the JHLPAA. Identify everything each team received, including any draft picks, and explain the transaction without assuming either manager's motives."
    )
    result = json.dumps(answer, ensure_ascii=False)
    assert answer['intent'] == 'fantasy_trade_investigation'
    assert 'No canonical trade matches' not in result
    assert 'Owen Power' in result and 'Tom Wilson' in result
    assert '2028' in result and 'Round 3' in result
    assert 'Bobby Orr received' in result
    assert 'Bubba’s Bruisers received' in result


def test_explicit_wrong_date_does_not_backfill_previous_trade():
    answer = _fantasy_trade_investigation(SimpleNamespace(transaction_history=_history()),
        "Explain the November 17 trade between Bobby Orr and Bubba's Bruisers in the JHLPAA.")
    assert 'No canonical trade matches' in json.dumps(answer)
