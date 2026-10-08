import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Athena.Inquiry.state import build_inquiry_state
from Athena.intent_planner import plan_capability
from Core.version import VERSION, RELEASE_HOTFIX

assert tuple(map(int, VERSION.split("."))) >= (0, 7, 7, 3, 4), VERSION
realistic='Is there a realistic trade opprotunity to acquire Connor McDavid without trading Auston Matthews?'
state=build_inquiry_state(realistic,'public'); plan=plan_capability(realistic,'public')
assert state.organizations == ['Toronto Maple Leafs'], state.to_dict()
assert state.protected_assets == ['Auston Matthews'], state.to_dict()
assert plan and plan.route == 'public_nhl_organizational_plausibility', plan

waived="Pretend the salary cap is not an issue, how would the Leafs get Connor McDavid without trading Matthews?"
state=build_inquiry_state(waived,'public'); plan=plan_capability(waived,'public')
assert 'salary_cap' in state.constraints_waived, state.to_dict()
assert 'salary_cap' not in state.constraints_enforced, state.to_dict()
assert state.scenario_mode == 'hypothetical', state.to_dict()
assert plan and plan.route == 'public_nhl_transaction_scenario', plan

source=open('Athena/capability_handlers.py',encoding='utf-8').read()
assert 'season_lines=' in source and 'P/GP' in source
assert 'before the September 29, 2026 regular-season start' in source and 'date.today()' in source
print('PASS: acceptance semantic routing, temporal public composition, and stale-state gating.')
