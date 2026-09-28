"""Validate isolated historical league acquisition/context contracts without network access."""
from __future__ import annotations
import inspect
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from Core.version import ATHENA_VERSION, RELEASE_NAME
from Knowledge.LeagueHistory.context import historical_entry, build_historical_context, extract_player_season_stats
from Providers.Fantrax.fantrax_client import FantraxClient

checks=[]
def check(name, ok, detail=''):
    checks.append(bool(ok)); print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")

print('Historical League Context Validation')
print('='*64)
entry=historical_entry(2025)
check('version_at_least_0_6_4_4_1', tuple(map(int,ATHENA_VERSION.split('.'))) >= (0,6,4,4,1), ATHENA_VERSION)
check('release_name_available', bool(RELEASE_NAME.strip()), RELEASE_NAME)
check('2025_registered', entry.get('league_id')=='jttzojgxme37biw2', entry)
registry=json.loads((ROOT/'Configuration/historical_leagues.json').read_text(encoding='utf-8'))
check('ten_historical_ids_registered', len(registry.get('historical_leagues',[]))==10, len(registry.get('historical_leagues',[])))
check('client_supports_context_override', 'league_id' in inspect.signature(FantraxClient).parameters and 'season' in inspect.signature(FantraxClient).parameters, inspect.signature(FantraxClient))
stats=extract_player_season_stats({'rows':[{'playerId':'p1','playerName':'Example','GP':56,'G':20,'A':45,'PTS':65}]})
check('gp_preserved', stats and stats[0]['games_played']==56, stats)
check('fantasy_ppg_points_per_game', stats and abs(stats[0]['points_per_game']-(65/56))<1e-9 and stats[0]['ppg_semantic']=='points_per_game', stats)
ctx=build_historical_context(season=2025,league_id=entry['league_id'],raw_payloads={'league_info':{},'player_stats':{'rows':[{'id':'p1','name':'Example','gamesPlayed':82,'points':90}]}},source_provenance={'player_stats':{'mode':'player_pool_evidence_fallback','league_id':entry['league_id'],'season':2025}})
check('league_identity_preserved', ctx['league_id']=='jttzojgxme37biw2' and ctx['season']==2025, (ctx['season'],ctx['league_id']))
check('historical_read_only', ctx['scope']=='historical_read_only' and ctx['active_workspace_mutation_allowed'] is False, ctx['scope'])
check('gp_first_class', ctx['production_normalization']['games_played_is_first_class'] is True, ctx['production_normalization'])
check('power_play_goals_unambiguous', ctx['production_normalization']['power_play_goals_field']=='power_play_goals', ctx['production_normalization'])
check('stats_provenance_preserved', ctx['source_provenance']['player_stats']['mode']=='player_pool_evidence_fallback', ctx['source_provenance'])
tool=(ROOT/'Tools/acquire_historical_league.py').read_text(encoding='utf-8')
check('scoped_tool_exists', bool(tool), 'Tools/acquire_historical_league.py')
check('player_pool_stats_fallback', 'player_pool_evidence_fallback' in tool and 'extract_player_season_stats(pool_payload)' in tool, 'conservative GP-backed fallback')
check('no_workspace_mutation', 'workspace.json' not in tool and 'write_text' not in tool, 'historical acquisition does not rewrite workspace config')
print('-'*64); print('Overall status:', 'PASS' if all(checks) else 'FAIL')
raise SystemExit(0 if all(checks) else 1)
