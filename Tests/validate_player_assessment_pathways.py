"""Player assessment invariants across identity, time windows, and career stage."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from Athena.player_assessment import assess_player, assessment_copy
from Core.version import ATHENA_VERSION
from Experience.player import deterministic_player_badges

checks=[]
def check(name, condition):
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")
    checks.append(bool(condition))

seasons=[
    {'season':'2025-26','gp':70,'points':78},
    {'season':'2024-25','gp':80,'points':92},
    {'season':'2023-24','gp':82,'points':94},
]
evidence={'source':'nhl_player_landing','target_season':'2025-26','season_history':seasons,
          'position':'C','age':38,'career_games':1500,'career_points':1800,'career_goals':600}
assessment=assess_player(evidence)
check('dated_three_season_current_rating',assessment['seasons_used']==3 and assessment['current_tier']=='Star')
check('independent_legacy',assessment['career_legacy']=='Career Superstar' and assessment['career_stage']=='Late Career Veteran')
check('separate_rendered_dimensions',deterministic_player_badges({'professional_assessment':assessment})==
      ['★★★★☆ Star','Career Superstar','Late Career Veteran'])
check('evidence_led_copy','2025-26, 2024-25, 2023-24' in assessment_copy('Example Player',evidence,assessment))
other={**evidence,'career_games':400,'career_points':400,'career_goals':130}
check('current_rating_unaffected_by_career_label',assess_player(other)['current_tier']==assessment['current_tier'] and
      assess_player(other)['career_legacy']!=assessment['career_legacy'])
old={**evidence,'target_season':'2028-29'}
check('stale_record_preserves_legacy_not_current',not assess_player(old)['current_tier'] and
      assess_player(old)['career_legacy']=='Career Superstar')
rookie={**evidence,'age':19,'career_games':60,'career_points':60,'career_goals':20,
        'season_history':[{'season':'2025-26','gp':60,'points':60}]}
r=assess_player(rookie)
check('rookie_stage_and_tags',r['career_stage']=='Rookie' and 'Development Potential' in r['rookie_tags'] and r['trend_provisional'])
check('version',tuple(map(int,ATHENA_VERSION.split('.'))) >= (0,6,5,9,0))
raise SystemExit(0 if all(checks) else 1)
