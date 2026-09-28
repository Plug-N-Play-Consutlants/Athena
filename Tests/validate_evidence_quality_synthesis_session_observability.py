from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from Core.version import ATHENA_VERSION, RELEASE_NAME
import Knowledge.Events.live_intelligence as li
from Scout.conversation.router import _compose_live_event_narrative, _event_followup_prompts
import Scout.app as app

fails=[]
def check(n,o,d=''):
 print(f"[{'PASS' if o else 'FAIL'}] {n}: {d}")
 if not o:fails.append(n)
print('Evidence Quality, Synthesis & Session Observability Validation'); print('='*72)
check('version',tuple(map(int, ATHENA_VERSION.split('.'))) >= (0,6,5,0,1),ATHENA_VERSION)
check('release',bool(RELEASE_NAME),RELEASE_NAME)
recent={'title':'Stars trim roster before opener','summary':'Dallas roster cuts','source_display_name':'NHL.com','published_at':'Fri, 25 Sep 2026 12:00:00 GMT','relevance_score':.8,'freshness_score':.8}
old={'title':'Stars offseason contract outlook','summary':'Dallas contract background','source_display_name':'NHL.com','published_at':'Tue, 14 Jul 2026 12:00:00 GMT','relevance_score':.8,'freshness_score':.8}
check('query_relative_freshness',li._query_freshness(recent,'Stars news')>li._query_freshness(old,'Stars news'),(li._query_freshness(recent,'Stars news'),li._query_freshness(old,'Stars news')))
check('historical_query_not_age_suppressed',li._query_freshness(old,'Stars history')==.8,li._query_freshness(old,'Stars history'))
strong=dict(recent,source_display_name='Sportsnet'); weak=dict(recent,source_display_name='NHLRumors.com')
check('source_authority_affects_quality',li._evidence_quality(strong,'Stars news')>li._evidence_quality(weak,'Stars news'))
events=[{'title':'Oilers put three on waivers','summary':'Edmonton trims its opening roster'},{'title':'Oilers reassign seven players','summary':'training camp roster cuts'}]
n=_compose_live_event_narrative('Oilers news',{'requested_event_types':[]},events)
check('evidence_derived_synthesis','roster and waiver decisions' in n,n)
prompts=_event_followup_prompts(events)
check('followups_derive_from_evidence',any('roster' in x.lower() or 'waiver' in x.lower() for x in prompts),prompts)
answer={'title':'Recent NHL events','intent':'live_event_intelligence','natural_language_response':'Synthesis','source_links':[{'title':'A','publisher':'NHL.com','url':'https://example.test/a'}],'more_source_links':[{'title':'B'}],'suggested_prompts':['Investigate A'],'observed_facts':['fact'],'known_limitations':['limit'],'developer':{'live_evidence':{'evidence_sufficiency':{'sufficient':True},'ignored_events':[{'title':'C','reasons':['non_matching_team']} ]}}}
record=app._session_answer_summary(answer)
check('session_preserves_primary',record.get('source_links')==answer['source_links'])
check('session_preserves_secondary',record.get('more_source_links')==answer['more_source_links'])
check('session_preserves_followups',record.get('suggested_prompts')==answer['suggested_prompts'])
check('session_preserves_diagnostics',record.get('developer',{}).get('live_evidence',{}).get('ignored_events')==answer['developer']['live_evidence']['ignored_events'])
print(f"Overall status: {'PASS' if not fails else 'FAIL'}")
raise SystemExit(1 if fails else 0)
