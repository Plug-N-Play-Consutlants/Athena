from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
raw = ROOT / 'Raw'
raw.mkdir(exist_ok=True)
(raw / 'league_info.json').write_text(json.dumps({'league': {'name': 'Test League'}, 'teams': [{'id': '1'}]}))
(raw / 'fantrax_player_pool.json').write_text(json.dumps({'players': [{'id': 'p1', 'name': 'Player One'}]}))
(raw / 'transactions.json').write_text(json.dumps({'pageError': {'code': 'WARNING_NOT_LOGGED_IN', 'message': 'Not logged in'}}))
print('fake partial fetch complete')
