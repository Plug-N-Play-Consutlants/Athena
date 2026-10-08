from __future__ import annotations
import sys
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from Athena.execution_registry import execute_specialist
from Scout.conversation.composition import compose_answer_payload, PUBLIC_COMPOSERS, REQUIRED_PUBLIC_COMPOSITION_INTENTS

def ck(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    return bool(ok)

def final(route,q):
    raw=execute_specialist(route,SimpleNamespace(files_loaded=[]),q,mode='public')
    return compose_answer_payload(raw)

def main():
    tests=[]
    tests.append(("required intents registered", REQUIRED_PUBLIC_COMPOSITION_INTENTS.issubset(PUBLIC_COMPOSERS.keys()), str(sorted(REQUIRED_PUBLIC_COMPOSITION_INTENTS-PUBLIC_COMPOSERS.keys()))))
    temporal=final('public_player_temporal_comparison','Show me Auston Matthews over the past 5 seasons')
    tests.append(("temporal public rows", 'Season-by-season:' in temporal.get('public_comment','') and '2025-26:' in temporal.get('public_comment',''), temporal.get('public_comment','')[:180]))
    tests.append(("visibility/render contracts separated", temporal.get('display_contract')=='public_comment_only' and temporal.get('experience_contract')=='athena_response_v1', f"{temporal.get('display_contract')} / {temporal.get('experience_contract')}"))
    tests.append(("internal narrative retained", 'verified NHL season records' in (temporal.get('diagnostics') or {}).get('internal_narrative',''), (temporal.get('diagnostics') or {}).get('internal_narrative','')[:120]))
    realistic=final('public_nhl_organizational_plausibility','Is there a realistic way for the Leafs to acquire McDavid without trading Matthews?')
    rt=realistic.get('public_comment','')
    tests.append(("plausibility public template", 'What is established:' in rt and 'Possible structures:' in rt and 'What keeps this from being a defensible named proposal:' in rt, rt[:220]))
    tests.append(("plausibility followups", len(realistic.get('suggested_prompts') or [])>=3, str(realistic.get('suggested_prompts'))))
    waived=final('public_nhl_transaction_scenario','Disregard salary cap, how could the Leafs trade for McDavid without moving Matthews?')
    wt=waived.get('public_comment','')
    tests.append(("waived public template", 'Ignoring the salary cap as requested' in wt and 'Possible structures:' in wt, wt[:220]))
    tests.append(("waived not internal dump", not wt.startswith('For this hypothetical, salary-cap feasibility is explicitly waived.'), wt[:120]))
    tests.append(("waived followups", len(waived.get('suggested_prompts') or [])>=3, str(waived.get('suggested_prompts'))))
    app=(ROOT/'Scout/app.py').read_text(encoding='utf-8')
    tests.append(("api final composition", 'answer = compose_answer_payload(answer)' in app and app.index('answer = compose_answer_payload(answer)') < app.index('turn_id = _record_session_turn', app.index('if path == "/api/ask"')), 'final compose precedes session record'))
    version=(ROOT/'Core/version.py').read_text(encoding='utf-8')
    tests.append(("version", 'VERSION_SCHEMA = "major.epic.sprint.patch.hotfix"' in version and 'ATHENA_VERSION = "0.7.7.3.4"' in version, 'canonical 0.7.7.3.4 version contract'))
    failed=0
    for name,ok,detail in tests:
        if not ck(name,ok,detail): failed+=1
    print(f"Overall status: {'PASS' if not failed else 'FAIL'}")
    return 0 if not failed else 1
if __name__=='__main__': raise SystemExit(main())
