from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from Core.version import ATHENA_VERSION, RELEASE_NAME
from Knowledge.Identity.registry import seed_identity_registry
import Knowledge.Events.live_intelligence as li

fails=[]
def check(n,o,d=''):
    print(f"[{'PASS' if o else 'FAIL'}] {n}: {d}")
    if not o: fails.append(n)

print('League-Wide Evidence Sufficiency Validation'); print('='*68)
check('version', tuple(map(int, ATHENA_VERSION.split('.'))) >= (0,6,5,0,1), ATHENA_VERSION)
check('release', bool(RELEASE_NAME), RELEASE_NAME)
registry=seed_identity_registry()
teams=[e for e in registry.all_entities() if e.entity_type=='team' and e.sport.lower()=='hockey' and e.league.lower()=='nhl']
check('nhl_32_team_identity_coverage', len(teams)==32, len(teams))
for prompt, expected in [('Oilers news','Edmonton Oilers'),('Maple Leafs news','Toronto Maple Leafs'),('Sharks news','San Jose Sharks'),('Utah Mammoth news','Utah Mammoth'),('Rangers news','New York Rangers')]:
    q=li._requested_team_discovery_queries(prompt)
    check('resolve_'+expected.lower().replace(' ','_'), expected in q, q)

former={'title':'Former Maple Leafs Forward signs contract with Flames','summary':'A former Toronto player has joined Calgary.','event_type':'news'}
ok,reasons=li._event_matches_filters(former, li._requested_team_terms('Maple Leafs news'), set())
check('historical_affiliation_rejected', not ok and 'historical_affiliation_only' in reasons, reasons)
current={'title':'Maple Leafs place Steven Lorentz on waivers','summary':'Toronto makes a current roster move.','event_type':'news'}
ok,reasons=li._event_matches_filters(current, li._requested_team_terms('Maple Leafs news'), set())
check('current_team_story_retained', ok, reasons)

thin=[{'title':"Oilers' Hyman discusses Babcock",'summary':'Edmonton Oilers camp update','source_display_name':'ESPN','url':'a','relevance_score':.9,'freshness_score':.9}]
s=li._evidence_sufficiency(thin,target_stories=6)
check('one_story_is_insufficient', not s['sufficient'], s)
topics=['waiver decisions','injury recovery','line combinations','prospect assignment','goalie workload','opening travel']
rich=[{'title':f'Edmonton Oilers {topics[i]}','summary':f'Oilers {topics[i]}','source_display_name':'ESPN' if i%2 else 'NHL.com','url':str(i),'relevance_score':.9,'freshness_score':.9} for i in range(6)]
s=li._evidence_sufficiency(rich,target_stories=6)
check('six_diverse_stories_sufficient', s['sufficient'], s)

# A surviving RSS match must no longer prevent discovery when coverage is thin.
orig_seed, orig_acquire, orig_discover = li.seed_live_feed_registry, li.acquire_live_rss_events, li.discover_current_news
class Feed:
    feed_id='fixture'; connector_type='live_rss'
class Reg:
    def by_sport(self,*args): return [Feed()]
class Result:
    events=[{'title':"Oilers' Hyman discusses Babcock",'summary':'Edmonton Oilers camp update','url':'https://espn.test/a','published_at':'now','event_type':'news','source_display_name':'ESPN'}]
def discover(query,**kwargs):
    return [
      {'event_id':f'd{i}','event_type':'news','sport':'nhl','league':'nhl','source_id':'news_search_discovery','feed_id':'current_news_discovery','source_display_name':'NHL.com' if i%2 else 'Sportsnet','title':f'Edmonton Oilers {topics[i % len(topics)]}','summary':f'Oilers {topics[i % len(topics)]}','url':f'https://news.test/{i}','published_at':'now','freshness_score':.86,'source_rank':.68,'source_mode':'fixture'}
      for i in range(8)
    ]
try:
    li.seed_live_feed_registry=lambda:Reg()
    li.acquire_live_rss_events=lambda *a,**k:Result()
    li.discover_current_news=discover
    out=li.select_live_evidence('Oilers news',allow_network=True,limit=12)
    check('thin_rss_triggers_discovery', out.get('acquisition_escalation')=='current_news_discovery', out.get('acquisition_escalation'))
    check('expanded_candidate_set', out.get('discovery_match_count',0)>=6, out.get('discovery_match_count'))
    check('sufficiency_exposed', 'evidence_sufficiency' in out, out.get('evidence_sufficiency'))
finally:
    li.seed_live_feed_registry, li.acquire_live_rss_events, li.discover_current_news = orig_seed, orig_acquire, orig_discover

router=(ROOT/'Scout/conversation/router.py').read_text(encoding='utf-8')
check('normal_mode_hides_rejection_telemetry','Athena also excluded' not in router,'rejected-item count remains developer evidence only')
print(f"Overall status: {'PASS' if not fails else 'FAIL'}")
raise SystemExit(1 if fails else 0)
