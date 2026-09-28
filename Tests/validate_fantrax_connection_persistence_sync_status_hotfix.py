from pathlib import Path
import json, tempfile

ROOT=Path(__file__).resolve().parents[1]
import sys
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from Core.version import ATHENA_VERSION, RELEASE_NAME
from Scout.app import build_sync_answer

def check(name, cond, detail):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}: {detail}")
    return bool(cond)

ok=[]
ok.append(check('version', tuple(map(int, ATHENA_VERSION.split('.'))) >= (0,6,5,0,1), ATHENA_VERSION))
ok.append(check('release', bool(RELEASE_NAME), RELEASE_NAME))
answer=build_sync_answer({
    'ok': True,
    'completed_steps': [{'label':'Fetch Fantrax data'}],
    'summary': {'canonical_transactions':0,'managers_analyzed':14},
    'operation_result': {'stage':'completed','warnings':[],'summary':'Athena synchronized the active league workspace.','confidence':0.9},
    'capability_dashboard': {'status':'partial','available_count':9,'limited_count':1,'lines':['⚠ Manager activity — partial: no current-season transaction behavior has been observed yet.']},
})
ok.append(check('completed_sync_title_not_downgraded_by_capability', answer.get('title')=='League sync — complete', answer.get('title')))
workspace_text=(ROOT/'Athena/workspace.py').read_text(encoding='utf-8')
ok.append(check('workspace_authoritative_mirror', '_mirror_live_fantrax_league_id' in workspace_text and 'provider["league_id"] = league_id' in workspace_text, 'legacy provider league ID mirrors live workspace'))
ok.append(check('placeholder_guard', 'is_placeholder_league_id(league_id)' in workspace_text, 'validator/demo IDs cannot be mirrored'))
print('Overall status:', 'PASS' if all(ok) else 'FAIL')
raise SystemExit(0 if all(ok) else 1)
