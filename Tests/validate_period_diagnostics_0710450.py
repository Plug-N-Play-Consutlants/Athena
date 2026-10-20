"""Source-level regression for bounded player-period diagnostic output."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Athena.Investigation.period_evidence_acquisition import acquire_player_period_production, inspect_player_stats_schema
class Fake:
    def __init__(self, *, league_id, season): pass
    def has_cookie_auth(self): return True
    def is_error_payload(self, payload): return False
    def get_player_stats(self, params=None):
        assert params == {'seasonOrProjection':'SEASON_31n_BY_PERIOD'}
        return {'season':'2026','period':2,'players':[{'player_id':'p','goals':2,'assists':3}]}
assert acquire_player_period_production(league_id='L',season='2026',period=2,client_factory=Fake)['verified']
class Wrong(Fake):
    def get_player_stats(self, params=None):
        return {'season':'2026','period':1,'players':[{'player_id':'p','goals':2,'assists':3}]}
assert acquire_player_period_production(league_id='L',season='2026',period=2,client_factory=Wrong)['status']=='unverified_period'
meta=inspect_player_stats_schema({'seasonOrProjections':[{'code':'SEASON_31n_BY_PERIOD','name':'Period'}, {'code':'SEASON_31n_YEAR_TO_DATE','name':'YTD'}]})
assert len(meta['season_option_metadata'])==1
assert meta['season_option_metadata'][0]['code']=='SEASON_31n_BY_PERIOD'
from Athena.decision_inquiry import execute_decision_inquiry
class Ctx: files_loaded=[]
reply=execute_decision_inquiry(Ctx(),'Toronto trade options with first-round pick over three years')
assert 'counterparty incentive' in reply['natural_language_response']
assert 'No specific player' in reply['natural_language_response']
print('PASS bounded provider diagnostics, temporal validation, decision gates')
