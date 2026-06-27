from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
out = ROOT / 'Output'
out.mkdir(exist_ok=True)
(out / 'player_pool_master.json').write_text(json.dumps({'record_count': 1, 'records': [{'id': 'p1'}]}))
print('fake player pool build complete')
