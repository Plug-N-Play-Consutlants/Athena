"""v67.19: enforce inquiry ownership, provider-authoritative editorial, diagnostics on demand."""
from datetime import datetime, timezone

import pytest

from Athena.audit_intent import affirmative_audit_request
from Athena.entry_policy import select_entry_route
from Athena.intent_resolution import select_executable_route
from Athena.Investigation.transaction_event_intelligence import resolve_reporting_periods
from Scout.conversation.role_intelligence import select_scout_role


PROMPT = (
    "Analyze the JHLPAA across completed scoring Periods 6, 7 and 8, using Period 5 as the baseline. "
    "Produce an engaging league editorial covering the championship race, standings movement, notable performances, "
    "trades, acquisitions and inactive teams. Use Fantrax as the authoritative source for fantasy points, standings, "
    "player contributions and transactions. Identify which players drove each team's performance where verified "
    "period-specific Fantrax statistics are available. Pay particular attention to Bubba's pursuit of first place "
    "and the November 18 fourteen-player trade between Grabner By the Jussi and No Regretzkys. "
    "Distinguish confirmed results from strategic interpretation. Do not independently recalculate fantasy points "
    "using NHL statistics or introduce scoring-reconciliation diagnostics unless a discrepancy investigation "
    "is specifically requested."
)


@pytest.mark.parametrize('mode', ['fantasy', 'public'])
def test_exact_failed_prompt_remains_provider_editorial(mode):
    assert not affirmative_audit_request(PROMPT)
    decision = select_entry_route(PROMPT, mode)
    assert decision.route == 'league_multi_period_analysis'
    assert select_executable_route(PROMPT, mode)[0] == decision.route
    assert select_scout_role(PROMPT, route=decision.route, mode=mode).role == 'journalist'
    assert resolve_reporting_periods(PROMPT) == [6, 7, 8]


@pytest.mark.parametrize('question', [
    'Reconcile JHLPAA scoring for Weeks 6 and 7 against NHL totals',
    'Audit JHLPAA scoring for Periods 6 and 7',
    'Verify JHLPAA points for Periods 6 and 7',
])
def test_explicit_scoring_investigation_remains_accessible(question):
    assert affirmative_audit_request(question)
    assert select_entry_route(question, 'public').reason == 'explicit_period_scoring_reconciliation'
    assert select_scout_role(question, route='league_recap').role == 'auditor'


@pytest.mark.parametrize('question', [
    'Do not audit JHLPAA scoring for Periods 6 and 7; just review standings and transactions.',
    'Review JHLPAA Periods 6 and 7 without reconciliation; report scores and trades.',
    'Analyze JHLPAA Periods 6 and 7. Do not verify scoring; use Fantrax standings and trades.',
])
def test_negated_audit_mentions_are_not_audit_requests(question):
    assert not affirmative_audit_request(question)
    assert select_entry_route(question, 'public').route != 'league_recap' or select_entry_route(question, 'public').reason != 'explicit_period_scoring_reconciliation'
    assert select_scout_role(question, mode='fantasy').role != 'auditor'


def test_freshness_sync_excludes_optional_scoring_diagnostics():
    from Athena.fantasy_refresh import ensure_fantasy_freshness
    recorded = []
    def fake_sync(**kwargs):
        recorded.append(kwargs)
        return {'ok': True}
    now = datetime(2026, 11, 25, tzinfo=timezone.utc)
    ws = lambda: {'workspace': {'league_id': 'league1', 'provider_key': 'fantrax',
                                 'last_sync_status': 'pending'}}
    outcome = ensure_fantasy_freshness(now=now, sync_fn=fake_sync, workspace_fn=ws)
    assert outcome['status'] == 'completed'
    assert recorded == [{'mode':'fantasy_league', 'provider':'Fantrax',
                         'fetch':True, 'include_diagnostics':False}]


def test_sync_plan_keeps_manual_audit_but_omits_it_from_routine_refresh():
    from Athena.sync import sync
    ordinary = sync(mode='fantasy_league', provider='Fantrax', dry_run=True, include_diagnostics=False)
    manual = sync(mode='fantasy_league', provider='Fantrax', dry_run=True, include_diagnostics=True)
    ordinary_ids = {stage['id'] for stage in ordinary['planned_steps']}
    manual_ids = {stage['id'] for stage in manual['planned_steps']}
    assert 'audit_historical_period_scoring' not in ordinary_ids
    assert 'audit_historical_period_scoring' in manual_ids
    assert 'fetch_fantrax_data' in ordinary_ids


def test_exact_editorial_dispatch_uses_provider_standings_without_nhl_attribution():
    from types import SimpleNamespace
    from unittest.mock import patch
    from Athena.Investigation.multi_period_analysis import investigate_multi_period
    from Tests.test_league_dynamics_0710677 import _snapshot
    context = SimpleNamespace(league_profile={'league_id':'jhlpaa1','season':2026},
                              standings_archive={}, transaction_history={'records':[]}, files_loaded=[])
    with (patch('Athena.Investigation.multi_period_analysis.load_snapshot',
                side_effect=lambda root, league, season, period: _snapshot(period)),
          patch('Athena.Investigation.nhl_period_production.acquire_nhl_period_production',
                side_effect=AssertionError('NHL audit must not run for ordinary editorial')),
          patch('Athena.Investigation.historical_roster_attribution.reconcile_period_points',
                side_effect=AssertionError('Historical scoring reconciliation must not run'))):
        answer = investigate_multi_period(context, PROMPT)
    assert answer['developer']['requested_periods'] == [6, 7, 8]
    assert answer['developer']['multi_period_findings']['status'] == 'verified'
    assert answer['developer']['multi_period_findings']['scoring_complete'] is True
    assert 'scoring audit' not in str(answer.get('title', '')).casefold()
