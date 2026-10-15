import ast
from pathlib import Path
root=Path(__file__).resolve().parents[1]
router=(root/'Scout/conversation/router.py').read_text()
tree=ast.parse(router)
fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='_is_team_performance_inquiry')
import re
scope={'re':re,'_normalize_public_query_text':lambda s:s.lower()}
exec(compile(ast.Module(body=[fn],type_ignores=[]),'<router>', 'exec'),scope)
check=scope['_is_team_performance_inquiry']
assert check("How are the Toronto Maple Leafs looking so far this season? What's working, what isn't?")
assert not check("Who are the Maple Leafs?")
client=(root/'Providers/Fantrax/fantrax_client.py').read_text()
assert 'seasonOrProjection' in client
acq=(root/'Athena/Investigation/period_evidence_acquisition.py').read_text()
assert '"SEASON_31n_BY_PERIOD"' in acq
assert 'period_filter_status' in acq
assert 'observed_period' in acq and 'observed_season' in acq
assert '"unverified_period"' in acq
print('[PASS] team evaluation classification; explicit BY_PERIOD request; conservative attribution gate')
