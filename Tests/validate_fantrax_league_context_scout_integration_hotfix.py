from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from Core.version import ATHENA_VERSION, RELEASE_NAME
from Providers.Fantrax.identity import resolve_league_name
from Providers.Fantrax.auth import connection_wizard
from Scout.conversation.router import analyze_league

def check(name, cond, detail):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}: {detail}")
    return bool(cond)

ok=[]
def version_tuple(value): return tuple(int(x) for x in str(value).split('.'))
ok.append(check('version_at_least_0_6_5_0_2', version_tuple(ATHENA_VERSION)>=version_tuple('0.6.5.0.2'), ATHENA_VERSION))
ok.append(check('release_name_available', bool(RELEASE_NAME), RELEASE_NAME))
ok.append(check('email_not_league_identity', resolve_league_name({'leagueName':'jesse.hill@rogers.com','leagueHistoryId':'qzgicmlmgrqq718y'})=='JHLPAA', resolve_league_name({'leagueName':'jesse.hill@rogers.com','leagueHistoryId':'qzgicmlmgrqq718y'})))
orig=connection_wizard.load_workspace
try:
    connection_wizard.load_workspace=lambda:{'workspace':{'league_id':'oldleague123'}}
    selected=connection_wizard.active_league_id('newleague456')
finally:
    connection_wizard.load_workspace=orig
ok.append(check('explicit_connection_selection_wins', selected=='newleague456', selected))
app=(ROOT/'Scout/app.py').read_text(encoding='utf-8')
ok.append(check('no_browser_league_id_persistence', "localStorage.setItem('athena.fantrax.league_id'" not in app, 'workspace/server is authoritative'))
ok.append(check('browser_stale_id_removed', "localStorage.removeItem('athena.fantrax.league_id')" in app, 'legacy browser value is cleared'))
ok.append(check('session_log_single_observed_facts_renderer', app.count('lines.append("Observed facts:")')==1, app.count('lines.append("Observed facts:")')))
ok.append(check('sync_restores_league_reading', 'answer["league_reading"] = league_reading' in app and 'Athena.ask("Analyze league", context=load_context()' in app, 'successful sync composes current league reading through Athena'))
router=(ROOT/'Scout/conversation/router.py').read_text(encoding='utf-8')
ok.append(check('no_obsolete_alpha_limitations', 'historical season trend fetching is not implemented in Scout Alpha' not in router and 'Natural-language answers are deterministic templates in this alpha' not in router, 'obsolete Alpha limitations removed from league analysis'))
answer=analyze_league()
text=str(answer.get('engine_conclusion') or '')
ok.append(check('league_analysis_uses_canonical_identity', 'JHLPAA' in text and 'jesse.hill@rogers.com' not in text, text[:220]))
ok.append(check('historical_coverage_visible', 'canonical historical draft coverage' in text.lower(), text[-180:]))
print('Overall status:', 'PASS' if all(ok) else 'FAIL')
raise SystemExit(0 if all(ok) else 1)
