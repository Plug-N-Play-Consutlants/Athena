"""Balanced non-network regression: shared capabilities must survive lens-specific work.

These checks are architectural sentinels, not claims of complete runtime answers.
"""
import ast
from pathlib import Path
root=Path(__file__).resolve().parents[1]
router=(root/'Scout/conversation/router.py').read_text(encoding='utf-8')
module=ast.parse(router)
functions={node.name:node for node in module.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))}
assert 'route_question' in functions
assert 'analyze_league' in functions
assert '_public_analytical_answer' in functions
assert '_is_team_performance_inquiry' in functions
route=ast.get_source_segment(router,functions['route_question'])
for marker in ('analyze_league(ctx, raw_question)', 'player_comparison_answer(', 'player_profile_answer(ctx, profile, raw_question)', '_public_analytical_answer('):
    assert marker in route, f'Lost established route: {marker}'
assert 'explicit_league = any(' in route and 'league_profile=getattr(ctx, "league_profile", None) if explicit_league else None' in route, 'Scout compatibility fallback must preserve an explicit league lens'
assert 'selected_mode = "public"' in route, 'Public NHL semantics must not inherit a stale fantasy lens'
assert route.index('orchestrated = athena_answer') < route.index('if selected_mode == "public":'), 'Athena registered routing must precede Scout compatibility fallbacks'
assert '_is_team_performance_inquiry(raw_question)' in route, 'Current-season questions must not fall into static team profiles'
acq=(root/'Athena/Investigation/period_evidence_acquisition.py').read_text(encoding='utf-8')
assert 'SEASON_31n_BY_PERIOD' in acq
assert 'unverified_period' in acq, 'Unverified Fantrax stats must not be promoted to weekly production'
assert 'period_filter_status' in acq
print('[PASS] balanced route sentinels: player, comparison, current-team, fantasy, period evidence')
