"""Production regression: 2026-11-18 league-export exchange and timeline."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import csv

from Athena.entry_policy import select_entry_route
from Athena.Investigation.transaction_event_intelligence import (
    investigate_transactions, resolve_reporting_periods, _event_datetime)
from Athena.Investigation.multi_period_analysis import investigate_multi_period
from Scout.conversation.multi_period_publication import publish_multi_period

FIXTURE=Path(__file__).parent/'fixtures'/'fantrax_nov18_14_player_trade.csv'
PROMPT=('Analyze the JHLPAA across completed Periods 6, 7 and 8, using Period 5 as the '
        'baseline. Cover the championship race, middle-table competition, lower-table '
        'developments, important transactions and emerging strategies.')


def _provider_calendar():
    # An illustrative test calendar, not a claim about the live provider schedule.
    return {'status':'calendar_closed','boundary_kind':'scoring','period':8,
            'schedule':{6:{'start':'2026-11-03','end':'2026-11-09'},
                        7:{'start':'2026-11-10','end':'2026-11-16'},
                        8:{'start':'2026-11-17','end':'2026-11-23'},
                        9:{'start':'2026-11-24','end':'2026-11-30'}}}


def _trade():
    rows=list(csv.DictReader(FIXTURE.open(encoding='utf-8',newline='')))
    return {'transaction_id':'fantrax:nov18_14_player_trade',
            'timestamp':rows[0]['Date (EST)'],'status':'executed',
            'season_week':int(rows[0]['Period']),'transaction_type':'trade',
            'summary':'Trade completed',
            'participants':[{'participant_name':t} for t in ('Grabner By the Jussi','No Regretzkys')],
            'assets':[{'asset_name':r['Player'],'asset_type':'player',
                       'movement_context':{'from_team_name':r['From'],'to_team_name':r['To']}}
                      for r in rows]}


def _snapshot(p):
    return {'period':p,'teams':[{'team_id':str(i),'name':f'Team {i:02d}',
             'rank':i,'points':230-i*9 + (p-5)*(20-i)} for i in range(1,15)]}


def test_scoring_period_baseline_not_selected_as_reporting_period():
    assert resolve_reporting_periods(PROMPT)==[6,7,8]
    assert select_entry_route(PROMPT,'public').route=='league_multi_period_analysis'


def test_csv_trade_is_one_event_with_all_14_destinations_and_no_picks():
    item=_trade()
    result=investigate_transactions({'records':[item]},[6,7,8],calendar=_provider_calendar())
    assert [p['count'] for p in result['periods']]==[0,0,1]
    event=result['spotlights'][0]
    assert event['event_period']==8
    assert event['roster_effective_period']==9
    assert event['event_period_source']=='provider_calendar_event_date'
    assert event['player_count']==14 and event['asset_count']==14 and event['pick_count']==0
    assert len(event['received']['Grabner By the Jussi'])==7
    assert len(event['received']['No Regretzkys'])==7
    assert 'commissioner' in event['asset_market_note']
    output=publish_multi_period({'status':'verified','periods':[6,7,8],
                                 'teams_analyzed':14,'transactions':result['periods'],
                                 'transaction_spotlights':result['spotlights']})
    assert '14-player exchange' in output
    assert 'Mitch Marner' in output and 'Matthew Knies' in output
    assert 'Period 9' in output and 'Week 8' in output
    assert 'limited available tradable picks' in output
    assert 'Weeks 6–8' in output and 'Weeks 5–8' not in output


def test_commissioner_attested_event_period_when_provider_calendar_missing():
    event=investigate_transactions({'records':[_trade()]},[6,7,8],calendar={'status':'unverified'})['spotlights'][0]
    assert event['event_period']==8 and event['event_period_source']=='league_commissioner_event_attestation'
    assert event['roster_effective_period']==9


def test_no_arbitrary_reclassification_without_calendar_or_attestation():
    other=_trade()
    other['transaction_id']='unrelated'
    other['assets']=other['assets'][:2]
    result=investigate_transactions({'records':[other]},[6,7,8],calendar=_provider_calendar())
    assert result['unresolved_count']==0 # date maps to Period 8, regardless of asset count
    assert result['periods'][-1]['count']==1
    assert result['spotlights'][0]['event_period_source']=='provider_calendar_event_date'
    unavailable=investigate_transactions({'records':[other]},[6,7,8],calendar={'status':'unverified'})
    assert sum(x['count'] for x in unavailable['periods'])==0
    assert unavailable['coverage']=='unverified_effective_period_fallback'


def test_end_to_end_reporting_window_and_significant_trade():
    ctx=SimpleNamespace(league_profile={'league_id':'fixture','season':2026},standings_archive={},
                        transaction_history={'records':[_trade()]},files_loaded=[])
    with patch('Athena.Investigation.multi_period_analysis.load_snapshot',side_effect=lambda o,l,s,p:_snapshot(p)),\
         patch('Athena.Investigation.fantrax_period_calendar.acquire_unified_period',return_value=_provider_calendar()):
        result=investigate_multi_period(ctx,PROMPT)
    out=result['natural_language_response']
    assert result['developer']['requested_periods']==[6,7,8]
    assert result['developer']['multi_period_findings']['teams_analyzed']==14
    assert 'Major 14-player exchange' in out
    assert 'Weeks 6–8' in out and 'Weeks 5–8' not in out
    assert result['developer']['multi_period_findings']['transaction_spotlights'][0]['event_period']==8


def test_roster_calendar_cannot_overrule_confirmed_approval_period():
    roster_calendar={**_provider_calendar(), 'boundary_kind':'points_based_roster_period',
                     'schedule':{8:{'start':'2026-11-10','end':'2026-11-17'},
                                 9:{'start':'2026-11-18','end':'2026-11-24'}}}
    trade=investigate_transactions({'records':[_trade()]},[6,7,8],calendar=roster_calendar)['spotlights'][0]
    assert trade['event_period']==8
    assert trade['roster_effective_period']==9
    assert trade['event_period_source']=='league_commissioner_event_attestation'
