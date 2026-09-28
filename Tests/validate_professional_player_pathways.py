"""Regression checks for distinct public identities, season evidence and veteran states."""
from __future__ import annotations
import sys
from pathlib import Path
from unittest.mock import patch
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Core.version import ATHENA_VERSION
from Knowledge.Intelligence.Public.player_evidence import player_evidence, player_tier
from Athena.player_assessment import assess_player
from Knowledge.Intelligence.Public.player_lifecycle import LifecycleEvidence, resolve_player_lifecycle
from Experience.player import deterministic_player_badges, build_current_stat_boxes

def check(label, good):
    print(f"[{'PASS' if good else 'FAIL'}] {label}")
    return good

payload = {'birthDate':'1997-07-26','position':'C','currentTeamAbbrev':'CAR','sweaterNumber':20,
           'headshot':'https://example.test/8478427.png',
           'seasonTotals':[{'season':season,'leagueAbbrev':'NHL','gameTypeId':2,
                            'gamesPlayed':79,'goals':27,'assists':points-27,'points':points,'plusMinus':11}
                           for season,points in [(20232024,78),(20242025,80),(20252026,82)]],
           'featuredStats':{'season':20252026,'regularSeason':{'subSeason':{
               'gamesPlayed':79,'goals':27,'assists':53,'points':80,'plusMinus':11},
               'career':{'gamesPlayed':900,'points':1100,'goals':310}}}}
identity = {'nhl_player_name':'Sebastian Aho','nhl_player_id':'8478427','nhl_team':'CAR','resolution_status':'resolved'}
checks = []
with patch('Knowledge.Intelligence.Public.player_evidence._records',return_value=([identity],{'8478427':payload})), \
     patch('Knowledge.Intelligence.Public.player_evidence._live_record',return_value=None):
    car = player_evidence('Sebastian Aho',team='CAR',position='C',birth_date='1997-07-26')
    swe = player_evidence('Sebastian Aho',team='NYI/AHL',position='D',birth_date='1996-02-17')
checks.append(check('same_name_never_borrows_other_player',not swe and car.get('stats',{}).get('+/-')==11))
zero_boxes = build_current_stat_boxes({'stats': {'goals': 29, 'assists': 45, 'points': 74, 'ppg': 1.088, '+/-': 0}}, {})
checks.append(check('recorded_zero_plus_minus_is_visible', next(box['value'] for box in zero_boxes if box['label'] == '+/-') == '0'))
checks.append(check('three_seasons_determine_current_tier',car.get('season')=='2025-26' and
                    player_tier(car)=='Star' and assess_player(car)['seasons_used']==3))
fake_client = ModuleType('Providers.NHL.nhl_client')
fake_client.NHLClient = lambda: type('Client', (), {'get_player_landing': lambda _, nhl_id: {**payload,'birthDate':'1989-12-08','position':'D','currentTeamAbbrev':'LAK'}})()
with patch('Knowledge.Intelligence.Public.player_evidence._records',return_value=([],{})), \
     patch('Knowledge.Intelligence.Public.player_evidence._season_index',return_value=[{'skaterFullName':'Drew Doughty','positionCode':'D','teamAbbrevs':'LAK','playerId':8474563}]), \
     patch('Knowledge.Intelligence.Public.player_evidence.os.getenv',return_value='1'), \
     patch.dict(sys.modules,{'Providers.NHL.nhl_client':fake_client}):
    recovered=player_evidence('Drew Doughty',team='LAK',position='D')
checks.append(check('official_missing_cache_lookup',recovered.get('nhl_id')=='8474563' and recovered.get('position')=='D'))
assessed=assess_player(car)
checks.append(check('current_and_legacy_independent',assessed['current_tier']=='Star' and
                    assessed['career_legacy']=='Career Superstar' and
                    deterministic_player_badges({'professional_assessment':assessed}, {})[:2]==['★★★★☆ Star','Career Superstar']))
stale={**car,'statistical_evidence':{**car['statistical_evidence'],'target_season':'2028-29','freshness':{**car['statistical_evidence'].get('freshness',{}),'status':'stale','stale_for_current_rating':True}}}
checks.append(check('stale_window_cannot_claim_current_tier',not assess_player(stale)['current_tier'] and
                    assess_player(stale)['career_legacy']=='Career Superstar'))
with patch('Knowledge.Intelligence.Public.player_lifecycle._local_player_rows',return_value=[
    LifecycleEvidence('fantrax_player_export','',.56,'nhl_roster_player','LAK','D',metadata={'GP':'72','Age':'36'})
]), patch('Knowledge.Intelligence.Public.player_lifecycle._news_evidence',return_value=[
    LifecycleEvidence('current_news_discovery','2026-09-27',.78,'organizational_prospect','LAK','',summary='Drew Doughty named Kings captain')
]):
    veteran = resolve_player_lifecycle('Drew Doughty',allow_network=True)
checks.append(check('headline_cannot_downgrade_veteran',veteran.get('lifecycle_state')=='nhl_roster_player'))
app=(ROOT/'Scout/app.py').read_text(encoding='utf-8')
checks.append(check('visible_professional_mode_retains_public_wire_value','<option value="public" selected>Professional Sports</option>' in app))
checks.append(check('player_age_rendered','identity.age' in app and 'Age ' in app))
checks.append(check('version_advanced',tuple(map(int,ATHENA_VERSION.split('.'))) >= (0,6,5,9,0)))
raise SystemExit(0 if all(checks) else 1)
