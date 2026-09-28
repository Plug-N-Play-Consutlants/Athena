from __future__ import annotations
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from Core.version import ATHENA_VERSION, RELEASE_NAME
from Core.text_utils import normalize_external_text

def check(label, ok, detail):
    print(f"[{'PASS' if ok else 'FAIL'}] {label}: {detail}"); return bool(ok)

def main():
    checks=[]
    checks.append(check('version',tuple(map(int, ATHENA_VERSION.split('.'))) >= (0,6,4,3,2),ATHENA_VERSION))
    checks.append(check('release',bool(RELEASE_NAME),RELEASE_NAME))
    for rel in ['Providers/Fantrax/fetch/fetch_draft_picks.py','Providers/Fantrax/build/draft_picks.py']:
        checks.append(check('required_file', (ROOT/rel).exists(), rel))
    sync=(ROOT/'Athena/sync.py').read_text(encoding='utf-8')
    checks.append(check('sync_step','build_draft_picks' in sync,'build_draft_picks'))
    router=(ROOT/'Scout/conversation/router.py').read_text(encoding='utf-8')
    checks.append(check('draft_intent','fantasy_draft_order' in router,'fantasy_draft_order'))
    checks.append(check('configured_slot_semantics','configured slots' in router and 'actually exercised' in router,'configured slots != guaranteed selections'))
    checks.append(check('future_ownership_wording','future draft assets' in router and 'original and current ownership' in router,'future ownership evidence preserved'))
    builder=(ROOT/'Providers/Fantrax/build/draft_picks.py').read_text(encoding='utf-8')
    checks.append(check('builder_semantics','configured_draft_slots' in builder and 'not_yet_determined' in builder,'draft board semantics explicit'))
    readiness=(ROOT/'Knowledge/knowledge_readiness.py').read_text(encoding='utf-8')
    checks.append(check('readiness_domain','canonical current/future draft asset records' in readiness,'draft_assets'))
    repaired=normalize_external_text('Bubbaâs Bruisers')
    checks.append(check('text_normalization', repaired == 'Bubba’s Bruisers', repaired))
    print('Overall status:', 'PASS' if all(checks) else 'FAIL')
    return 0 if all(checks) else 1
if __name__=='__main__': raise SystemExit(main())
