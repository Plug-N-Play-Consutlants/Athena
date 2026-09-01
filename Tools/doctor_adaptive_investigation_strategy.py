"""Doctor for Adaptive Investigation Strategy Foundation."""
from __future__ import annotations
from pathlib import Path
import sys
PROJECT_ROOT=Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0,str(PROJECT_ROOT))
from Core.version import ATHENA_VERSION, RELEASE_NAME
from Intelligence.Investigation import investigation_diagnostics, build_investigation_plan

def main():
    checks=[]
    def add(label,ok,detail): checks.append((label,ok,detail))
    add('version',ATHENA_VERSION>='0.6.4.0.0',ATHENA_VERSION)
    add('release',RELEASE_NAME in {'Adaptive Investigation Strategy Foundation','Adaptive Investigation Runtime Integration'},RELEASE_NAME)
    diag=investigation_diagnostics(); add('diagnostics',diag.get('status')=='pass',diag)
    add('rich_profile_preserved',build_investigation_plan('public_player_profile').strategy.preserve_rich_output,build_investigation_plan('public_player_profile').strategy.depth)
    add('rich_comparison_preserved',build_investigation_plan('public_player_comparison').strategy.preserve_rich_output,build_investigation_plan('public_player_comparison').strategy.depth)
    add('brief_score',build_investigation_plan('score_update').strategy.depth=='concise',build_investigation_plan('score_update').strategy.depth)
    add('brief_news',build_investigation_plan('live_event_intelligence').strategy.depth=='concise',build_investigation_plan('live_event_intelligence').strategy.depth)
    print('Adaptive Investigation Strategy Doctor'); print('='*68)
    for label,ok,detail in checks: print(f"[{'PASS' if ok else 'FAIL'}] {label}: {detail}")
    passed=all(ok for _,ok,_ in checks); print('-'*68); print('Overall status: '+('PASS' if passed else 'FAIL'))
    return 0 if passed else 1
if __name__=='__main__': raise SystemExit(main())
