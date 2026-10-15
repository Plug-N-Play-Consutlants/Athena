from __future__ import annotations
import sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from Athena.Investigation.evidence_dossier import build_dossier
from Athena.Inquiry.execution import summarize_recent_league_activity
from Core.version import ATHENA_VERSION
assert tuple(map(int, ATHENA_VERSION.split('.'))) >= (0, 7, 10, 0, 0)
records={'records':[
 {'transaction_id':'old','period':2,'timestamp':'2026-10-12T18:00:00Z','transaction_type':'free_agent_add','team_name':'Old'},
 {'transaction_id':'trade','period':3,'timestamp':'2026-10-06T18:00:00Z','transaction_type':'trade','summary':'Trade completed',
  'participants':[{'team_name':'Bubba'},{'team_name':'Hronek'}],
  'assets':[{'asset_type':'player','asset_name':'Jack Eichel'},{'asset_type':'draft_pick','asset_name':'2028 Round 1'}]},
 {'transaction_id':'add','period':3,'timestamp':'2026-10-06T18:00:00Z','transaction_type':'free_agent_add','team_name':'Reapers'}
]}
a=summarize_recent_league_activity(records,period=3,now=datetime(2026,10,13,tzinfo=timezone.utc))
assert a['transaction_count']==2 and a['team_count']==3,a
assert a['scope_method']=='explicit_period'
assert 'Jack Eichel' in a['highlights'][0]['summary']
d=build_dossier(subject='week',requirements=['transactions','standings','player_performance'],evidence={'transactions':a},findings=[{'summary':a['highlights'][0]['summary'],'source_id':'trade'}])
assert d['coverage']['transactions']=='available' and d['missing']==['standings','player_performance'],d
assert d['findings'][0]['source_id']=='trade'
print('PASS | version, period authority, actor recovery, trade detail, evidence coverage and provenance')
