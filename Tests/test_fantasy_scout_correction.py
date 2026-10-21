import unittest
from datetime import datetime,timezone,timedelta
from Athena.entry_policy import select_entry_route
from Athena.intent_resolution import select_executable_route
from Athena.fantasy_refresh import ensure_fantasy_freshness
Q='Produce the JHLPAA weekly league report for the most recently completed scoring period. Identify the correct Monday–Sunday reporting window.'
class TestFantasyScoutCorrection(unittest.TestCase):
 def test_editorial_route(self):
  self.assertEqual(select_entry_route(Q,'fantasy').route,'league_recap')
  self.assertEqual(select_executable_route(Q,'fantasy')[0],'league_recap')
 def test_freshness(self):
  now=datetime.now(timezone.utc); calls=[]
  def ws(age):return {'workspace':{'league_id':'x','provider_key':'fantrax','last_sync_at':(now-timedelta(minutes=age)).isoformat(),'last_sync_status':'completed'}}
  self.assertEqual(ensure_fantasy_freshness(now=now,workspace_fn=lambda:ws(1),sync_fn=lambda **kw:calls.append(kw))['status'],'fresh')
  self.assertEqual(len(calls),0)
  self.assertEqual(ensure_fantasy_freshness(now=now,workspace_fn=lambda:ws(120),sync_fn=lambda **kw:(calls.append(kw) or {'ok':True}))['status'],'completed')
  self.assertEqual(len(calls),1)
 def test_failure_fallback(self):
  s=ensure_fantasy_freshness(workspace_fn=lambda:{'workspace':{'league_id':'x'}},sync_fn=lambda **kw:(_ for _ in ()).throw(RuntimeError('offline')))
  self.assertEqual(s['status'],'failed')
if __name__=='__main__':unittest.main()
