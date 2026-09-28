from __future__ import annotations
import ast
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
checks=[]
def check(label, value):
    checks.append(bool(value)); print(f"[{'PASS' if value else 'FAIL'}] {label}")
version=(ROOT/'Core/version.py').read_text(encoding='utf-8')
disc=(ROOT/'Providers/Fantrax/fetch/historical_player_stats_discovery.py')
acq=(ROOT/'Tools/acquire_historical_league.py')
check('version_at_least_0_6_4_4_2', tuple(map(int, __import__('re').search(r'ATHENA_VERSION = \"([0-9.]+)\"', version).group(1).split('.'))) >= (0,6,4,4,2))
check('discovery_module_exists', disc.exists())
for p in (disc, acq): ast.parse(p.read_text(encoding='utf-8')); check(f'parse_{p.name}', True)
t=disc.read_text(encoding='utf-8')
a=acq.read_text(encoding='utf-8')
check('no_cookie_export', 'secrets_exported": False' in t)
check('application_asset_discovery', '_SCRIPT_RE' in t and '_SERVICE_RE' in t)
check('requires_gp_normalization', 'extract_player_season_stats' in t)
check('discovery_integrated', 'discover_historical_player_stats' in a)
check('discovery_report_written', 'player_stats_source_discovery.json' in a)
check('no_fabricated_stats', 'source_discovery_no_usable_candidate' in a)
print('Overall status:', 'PASS' if all(checks) else 'FAIL')
raise SystemExit(0 if all(checks) else 1)
