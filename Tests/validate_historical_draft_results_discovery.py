"""Validate Historical Draft Results source discovery without network access."""
from __future__ import annotations
import inspect
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from Core.version import ATHENA_VERSION, RELEASE_NAME
from Providers.Fantrax.fetch import historical_draft_results_discovery as discovery

checks=[]
def check(name, ok, detail=''):
    checks.append(bool(ok)); print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")

print('Historical Draft Results Source Discovery Validation')
print('='*72)
source=inspect.getsource(discovery)
tool=(ROOT/'Tools/acquire_historical_league.py').read_text(encoding='utf-8')
check('version_at_least_0_6_4_5_1', tuple(map(int, ATHENA_VERSION.split('.'))) >= (0,6,4,5,1), ATHENA_VERSION)
check('known_surface', '/fantasy/league/{client.league_id}/draft-results' in source, 'league-scoped Draft Results page')
check('authenticated_session', 'client.session.get(page_url' in source, 'existing Fantrax session')
check('documented_draft_results_endpoint', 'general/getDraftResults' in source, 'Fantrax Beta API documented endpoint')
check('documented_endpoint_first', source.index('documented_endpoint = \"general/getDraftResults\"') < source.index('for path in sorted(service_candidates)'), 'documented endpoint precedes fallback discovery')
check('application_asset_discovery', '_SCRIPT_RE' in source and 'assets[:max_assets]' in source, 'page + Fantrax JS assets')
check('read_style_fxpa_only', '_METHOD_RE' in source and 'client.fxpa_request' in source, 'discovered read-style methods only')
check('structural_selection_evidence', '_draft_result_score' in source and 'playerid' in source.lower() and 'round' in source.lower() and 'pick' in source.lower(), 'selection-like structure required')
check('secrets_not_exported', '"secrets_exported": False' in source, 'safe report contract')
check('separate_from_draft_picks', 'payloads["draft_results"]' in tool and 'payloads["draft_picks"]' not in tool, 'separate historical payload capability')
check('raw_results_written', 'draft_results.json' in tool, 'Raw/Historical/<season>/draft_results.json')
check('discovery_report_written', 'draft_results_source_discovery.json' in tool, 'safe discovery report')
check('no_workspace_mutation', 'workspace.json' not in tool and 'write_text' not in tool, 'historical read-only isolation')
print('-'*72); print('Overall status:', 'PASS' if all(checks) else 'FAIL')
raise SystemExit(0 if all(checks) else 1)
