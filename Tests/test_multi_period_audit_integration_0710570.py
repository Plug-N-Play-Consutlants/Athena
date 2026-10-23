"""v57 acceptance: requested periods, source-verifiable reports, and sync diagnostics."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from Athena.Investigation.period_execution import _requested_periods, _explicit_period_request
from Athena.Investigation.multi_period_audit import investigate_requested_periods
from Athena.Investigation.sync_period_scoring_audit import run
from Scout.conversation.league_recap_narrative import compose_period_report
from Tests.test_universal_scoring_integrity_0710560 import _snap, _league, FakeFantrax, _window


def test_explicit_period_lists_preserved_not_reduced_to_first_match():
    cases = {
        'Reconcile JHLPAA scoring for Weeks 2 and 3 using ACTIVE players': [2, 3],
        'Reconcile Period 2 and Period 3': [2, 3],
        'Week 2 through Week 4': [2, 3, 4],
        'Periods 2, 3 and 4': [2, 3, 4],
        'Week 3 recap October 12-19, 2026': [3],
        'Report October 12-19, 2026': [],
    }
    for question, expected in cases.items():
        assert _requested_periods(question) == expected, question
    assert _explicit_period_request('Report for October 12–18, 2026')[1] is not None


def test_targeted_period_audit_does_not_overwrite_sync_status(tmp_path):
    _snap(tmp_path)
    kw = dict(league_info=_league(), league_id='league1', season=2026,
              expected_teams=2, client_factory=FakeFantrax, nhl_acquirer=_window,
              output_dir=tmp_path, clock=datetime(2026, 10, 21, tzinfo=timezone.utc))
    synced = run(**kw)
    sync_original = (tmp_path/'PeriodScoringAudit'/'sync_manifest.json').read_bytes()
    requested = run(**kw, requested_periods=[3, 2])
    assert requested['audit_scope'] == 'explicit_request'
    assert requested['attempted_count'] == 2
    assert sorted(requested['periods']) == ['2', '3']
    assert (tmp_path/'PeriodScoringAudit'/'sync_manifest.json').read_bytes() == sync_original
    assert json.loads((tmp_path/'PeriodScoringAudit'/'request_manifest.json').read_text())['attempted_count'] == 2
    assert synced['status'] == requested['status'] == 'partial'


def test_request_reader_contains_both_periods_team_deltas_and_reserve_exclusions(tmp_path):
    _snap(tmp_path)
    def runner(**kwargs):
        return run(league_info=_league(), client_factory=FakeFantrax,
                   nhl_acquirer=_window, clock=datetime(2026,10,21,tzinfo=timezone.utc), **kwargs)
    report = investigate_requested_periods(output_dir=tmp_path, league_id='league1',
                season=2026, periods=[2,3], expected_teams=2, runner=runner)
    assert report['status'] == 'audited'
    assert report['requested_periods'] == [2,3]
    assert report['audited_periods'] == 2
    assert [p['period'] for p in report['periods']] == [2,3]
    for week in report['periods']:
        assert week['team_count'] == 2 and week['numeric_matched_teams'] == 1
        assert week['identity_complete_teams'] == 1
        assert week['teams'][0]['difference'] == 2
        assert week['teams'][0]['unmatched_active_ids'] == ['f2']
        assert week['teams'][0]['reserve_nhl_points_excluded'] == 8
        assert week['teams'][1]['difference'] == 0
        assert all(t['lineup_eligibility'] == 'period_snapshot_not_game_effective'
                   for t in week['teams'])


def test_future_week_remains_explicitly_unverified(tmp_path):
    _snap(tmp_path)
    def runner(**kwargs):
        return run(league_info=_league(), client_factory=FakeFantrax,
                   nhl_acquirer=_window, clock=datetime(2026,10,21,tzinfo=timezone.utc), **kwargs)
    result = investigate_requested_periods(output_dir=tmp_path, league_id='league1',
                  season=2026, periods=[2,4], expected_teams=2, runner=runner)
    assert result['status']=='partial'
    assert result['audited_periods'] == 1
    assert result['periods'][1]['status'] == 'source_unavailable'
    assert 'not closed' in result['periods'][1]['reason']


def test_missing_standings_does_not_generate_numeric_teams(tmp_path):
    def runner(**kwargs):
        return run(league_info=_league(), client_factory=FakeFantrax,
                   nhl_acquirer=_window, clock=datetime(2026,10,21,tzinfo=timezone.utc), **kwargs)
    result = investigate_requested_periods(output_dir=tmp_path, league_id='league1',
                  season=2026, periods=[2,3], expected_teams=2, runner=runner)
    assert result['status'] == 'source_unavailable' and result['audited_periods'] == 0
    assert all(not r['teams'] for r in result['periods'])
    assert all('baseline' in r['reason'].lower() for r in result['periods'])


def test_misidentified_archive_cannot_supply_cross_period_teams(tmp_path):
    def fake_runner(**kwargs):
        path = tmp_path/'PeriodScoringAudit'/'league1'/'2026'/'period_002.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'schema':'athena.period_attribution.v1','league_id':'other',
           'season':'2026','period':2,'teams':[{'team_id':'t1'}]}))
        return {'periods':{'2':{'status':'numeric_complete','team_count':1}}}
    result = investigate_requested_periods(output_dir=tmp_path,league_id='league1',
                    season=2026,periods=[2],expected_teams=1,runner=fake_runner)
    assert result['status']=='source_unavailable'
    assert result['periods'][0]['teams']==[]
    assert 'source' in result['periods'][0]['reason']


def test_scout_multi_period_presentation_names_each_team_and_exception():
    multi = {'requested_periods':[2,3], 'periods':[
      {'period':2,'status':'numeric_complete','numeric_matched_teams':2,
       'identity_complete_teams':2,'team_count':2,'reserve_nhl_points_excluded':8,
       'teams':[{'team_name':'One','difference':0,'fantrax_points':5,'unmatched_active_ids':[]},
                {'team_name':'Two','difference':0,'fantrax_points':2,'unmatched_active_ids':[]}]},
      {'period':3,'status':'partial','numeric_matched_teams':1,
       'identity_complete_teams':1,'team_count':2,'reserve_nhl_points_excluded':4,
       'teams':[{'team_name':'Waterbury','difference':2,'fantrax_points':38,
                 'identified_active_nhl_points':36,'unmatched_active_ids':['f6']},
                {'team_name':'Justin','difference':0,'fantrax_points':30,'unmatched_active_ids':[]}]},
    ]}
    research={'schema':'athena.league_period_research.v2','league_name':'JHLPAA',
              'period':3,'findings':[],'coverage':{},'multi_period_scoring':multi}
    rendered = compose_period_report(research=research)
    assert 'Week 2: 2/2' in rendered
    assert 'Week 3: 1/2' in rendered
    assert 'Waterbury: 36 NHL ACTIVE vs 38 Fantrax (difference +2); unresolved ACTIVE IDs: f6.' in rendered
    assert 'Justin: 30/30 numeric match' in rendered
    assert '8 NHL reserve points excluded' in rendered
    assert 'not proof of game-by-game' in rendered


def test_debug_export_includes_optional_sync_audit_outcome(tmp_path, monkeypatch):
    from Athena import debug_export
    audit_dir = tmp_path/'PeriodScoringAudit'
    audit_dir.mkdir()
    (audit_dir/'sync_manifest.json').write_text(json.dumps({'schema':'athena.period_scoring_audit_manifest.v1',
      'status':'partial','attempted_count':2,'numeric_complete_periods':0,
      'periods':{'2':{'status':'source_unavailable','reason':'standings baseline missing'},
                 '3':{'status':'partial','numeric_matched_teams':13,'team_count':14,
                      'point_discrepancies':[{'team_name':'Waterbury','difference':2}]}}}))
    (tmp_path/'player_identity_coverage.json').write_text(json.dumps({'historical_periods_with_gaps':2}))
    monkeypatch.setattr(debug_export,'OUTPUT_DIR',tmp_path)
    monkeypatch.setattr(debug_export,'RAW_DIR',tmp_path)
    monkeypatch.setattr(debug_export,'get_status',lambda:{'workspace':{
      'provider':'Fantrax','last_operation_result':{'metadata':{'completed_steps':[
        {'id':'audit_historical_period_scoring','status':'warning',
         'validation_message':'Audit unavailable for Week 2'}]}}}})
    monkeypatch.setattr(debug_export,'assess_capabilities',lambda p:{})
    monkeypatch.setattr(debug_export,'capability_dashboard',lambda r:{'lines':[]})
    result = debug_export.build_debug_export()
    detail = result['scoring_audit_diagnostics']
    assert detail['sync_step']['status']=='warning'
    assert detail['sync_manifest']['periods']['2']['reason']=='standings baseline missing'
    assert detail['identity_coverage']['historical_periods_with_gaps']==2


def test_full_scout_entry_routes_both_requested_weeks_to_athena(monkeypatch, tmp_path):
    from unittest.mock import patch
    from datetime import date
    from Athena.Investigation.fantrax_period_calendar import resolve_unified_period
    from Athena.Investigation.standings_archive import save_snapshot
    from Scout.conversation.context import ScoutContext
    from Scout.conversation.router import route_question
    from Tests.test_weekly_report_acceptance import PERIODS, _snapshot, _UnauthenticatedFantrax

    save_snapshot(tmp_path, _snapshot(1, 2, 40, 1, 50))
    save_snapshot(tmp_path, _snapshot(2, 2, 90, 1, 100))
    save_snapshot(tmp_path, _snapshot(3, 1, 150, 2, 110))
    unified = resolve_unified_period({'data':{'scoringPeriods':PERIODS,'rosterPeriods':PERIODS}},
                                     today=date(2026,10,21))
    ctx = ScoutContext(league_profile={'league_id':'jhlpaa1','season':2026,
                       'league_name':'JHLPAA','team_count':2,'sport':'NHL','keeper_count':11},
                       standings_archive={'league_id':'jhlpaa1','season':2026},
                       team_profiles=[],manager_behavior={},league_market={},
                       knowledge_readiness={},transaction_history={'records':[]},player_master=[])
    seen = []
    def collect(**kw):
        seen.extend(kw['periods'])
        return {'status':'partial','requested_periods':kw['periods'],
                'audited_periods':1,'unavailable_periods':1,'periods':[
          {'period':2,'status':'source_unavailable','reason':'prior NHL source unavailable'},
          {'period':3,'status':'partial','numeric_matched_teams':1,
           'identity_complete_teams':1,'team_count':2,'reserve_nhl_points_excluded':3,
           'teams':[{'team_name':'Alpha','difference':0,'fantrax_points':60,'unmatched_active_ids':[]},
                    {'team_name':'Beta','difference':2,'fantrax_points':12,
                     'identified_active_nhl_points':10,'unmatched_active_ids':[]}]},
        ]}
    with (patch('Core.project_paths.OUTPUT_DIR',tmp_path),
          patch('Athena.fantasy_refresh.ensure_fantasy_freshness',
                return_value={'status':'fresh','attempted':False}),
          patch('Athena.Investigation.fantrax_period_calendar.acquire_unified_period',
                return_value=unified),
          patch('Providers.Fantrax.fantrax_client.FantraxClient',_UnauthenticatedFantrax),
          patch('Athena.Investigation.period_evidence_acquisition.acquire_player_period_production',
                return_value={'status':'unverified_period','verified':False,
                              'records':[],'reason':'no period proof','diagnostic':{}}),
          patch('Athena.Investigation.multi_period_audit.investigate_requested_periods',collect)):
        answer = route_question('Reconcile JHLPAA scoring for Weeks 2 and 3, using ACTIVE players and NHL games. '
                 'Then produce the Week 3 editorial report covering standings and trades.',
                 ctx=ctx,mode='public')
    assert answer['developer']['athena_request']['selected_route'] == 'league_recap'
    assert answer['developer']['period_selection']['period'] == 3
    assert seen == [2,3]
    text = answer['natural_language_response']
    assert 'Week 2: not audited — prior NHL source unavailable' in text
    assert 'Week 3: 1/2 numerically matched' in text
    assert 'Beta: 10 NHL ACTIVE vs 12 Fantrax (difference +2)' in text
    assert any('Requested scoring periods: 2, 3' in fact for fact in answer['observed_facts'])


def test_direct_scoring_audit_request_routes_without_editorial_keywords():
    from Athena.entry_policy import select_entry_route
    for mode in ('fantasy','public'):
        outcome = select_entry_route('Reconcile JHLPAA scoring for Weeks 2 and 3',mode)
        assert outcome.route == 'league_recap'
        assert outcome.reason == 'explicit_period_scoring_reconciliation'
