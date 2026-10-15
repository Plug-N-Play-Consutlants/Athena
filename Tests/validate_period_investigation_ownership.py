"""Architectural ownership gate for the league-period investigation."""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
router = ast.parse((ROOT / 'Scout/conversation/router.py').read_text(encoding='utf-8'))
executor = ast.parse((ROOT / 'Athena/Investigation/period_execution.py').read_text(encoding='utf-8'))

def method(tree, name):
    return next(node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name)

route = method(router, 'analyze_league')
exec_fn = method(executor, 'execute_league_period')
route_imports = [n.module for n in ast.walk(route) if isinstance(n, ast.ImportFrom)]
assert 'Athena.Investigation.period_execution' in route_imports
assert 'Providers.Fantrax.fantrax_client' not in route_imports, 'Scout must not acquire provider data'
assert 'Athena.Investigation.standings_acquisition' not in route_imports, 'Scout must not sequence standings'
assert 'Athena.Investigation.recap_context' not in route_imports, 'Scout must not reconcile context'
assert 'Athena.Investigation.recap_evidence_plan' not in route_imports, 'Scout must not audit acquisition'
exec_imports = [n.module for n in ast.walk(exec_fn) if isinstance(n, ast.ImportFrom)]
for dependency in ('Athena.Investigation.standings_acquisition', 'Athena.Investigation.recap_context', 'Athena.Investigation.recap_evidence_plan', 'Athena.Investigation.league_recap'):
    assert dependency in exec_imports, f'Executor no longer uses {dependency}'
assert not any((n.module or '').startswith('Scout') for n in ast.walk(exec_fn) if isinstance(n, ast.ImportFrom)), 'Athena must not import Scout'
import sys
sys.path.insert(0, str(ROOT))
from Core.version import ATHENA_VERSION, RELEASE_HOTFIX
assert ATHENA_VERSION.split('.')[-1] == RELEASE_HOTFIX, 'Version metadata mismatch'
print('[PASS] Period investigation ownership and version consistency')
