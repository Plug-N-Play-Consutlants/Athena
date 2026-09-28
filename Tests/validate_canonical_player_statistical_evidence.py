"""Validate one canonical NHL statistical evidence contract across consumers."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from Knowledge.Intelligence.Public.player_evidence import build_statistical_evidence
from Athena.player_assessment import assess_player
from Core.version import ATHENA_VERSION

checks=[]
def check(name, condition):
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")
    checks.append(bool(condition))

series=[
 {'season':'2025-26','gp':82,'goals':44,'assists':94,'points':138,'plus_minus':20},
 {'season':'2024-25','gp':67,'goals':26,'assists':74,'points':100,'plus_minus':10},
 {'season':'2023-24','gp':76,'goals':32,'assists':100,'points':132,'plus_minus':35},
]
stat=build_statistical_evidence(season_history=series,career={'gamesPlayed':800,'points':1100,'goals':350},target_season='2026-27')
check('canonical_contract',stat['contract']=='canonical_player_statistical_evidence')
check('full_multi_season_series',len(stat['season_series'])==3 and stat['latest_observed_season']['points']==138)
check('career_totals_normalized',stat['career']=={'games':800,'points':1100,'goals':350})
check('freshness_separate_from_availability',stat['freshness']['status']=='current_or_recent' and stat['season_count']==3)
stale=build_statistical_evidence(season_history=series[2:],career={'gamesPlayed':190,'points':50,'goals':12},target_season='2026-27')
check('stale_history_retained',stale['season_count']==1 and stale['freshness']['stale_for_current_rating'])
evidence={'statistical_evidence':stat,'season_history':[], 'target_season':'2026-27','position':'C','age':29,
          'career_games':800,'career_points':1100,'career_goals':350,'awards':[],'source':'nhl_player_landing'}
check('assessment_consumes_canonical_contract',assess_player(evidence)['seasons_used']==2 and len(evidence['statistical_evidence']['season_series'])==3)
check('version',ATHENA_VERSION=='0.6.5.10.8')
raise SystemExit(0 if all(checks) else 1)
