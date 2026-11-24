"""Regression for real Week 6 wording and 3/14 partial score coverage."""
from Athena.entry_policy import select_entry_route
from Athena.Investigation.scoring_coverage_diagnostics import summarize_attribution_coverage
from Scout.conversation.journalist_composition import compose_journalist_report, audit_publication
from Scout.conversation.router import _conversational_league_recap


def week6():
    return {'schema': 'athena.league_period_research.v2', 'league_name': 'JHLPAA',
            'period': 6, 'period_calendar': {'start': '2026-11-02', 'end': '2026-11-09'},
            'findings': [{'kind': 'surge', 'team': 'Bubba’s Bruisers', 'period_points': 68,
                          'rank': 2, 'rank_change': 1, 'top_score': True},
                         {'kind': 'secondary_market', 'transaction_count': 6,
                          'examples': ['Leeeroy Jenkins added Emmitt Finnie']}],
            'editorial': {'trades': [], 'trade_count': 0},
            'period_scoring_audit': {'status': 'partial', 'team_count': 14, 'reconciled_teams': 3,
                                     'unreconciled_teams': 11},
            'editorial_player_attribution': {'status': 'reconciled_snapshot', 'period': 6,
                                             'records': [{'player_name': 'Connor McDavid',
                                                          'fantasy_team': 'Leeeroy Jenkins', 'points': 9,
                                                          'attribution_kind': 'historical_active_snapshot_numeric_reconciliation',
                                                          'credited_points_verified': False}]}}


def test_public_named_league_previous_week_route_without_magic_words():
    question = 'Give me a summary of the previous week in the JHLPAA'
    assert select_entry_route(question, 'public').route == 'league_recap'
    assert _conversational_league_recap(question, 'public')
    assert select_entry_route('What happened in the NHL last week?', 'public').route != 'league_recap'


def test_week6_no_trade_correct_wording_and_partial_scoring():
    research = week6()
    report = compose_journalist_report(research=research)
    assert 'November 2–9, 2026' in report
    assert 'The league recorded 6 roster moves' in report
    assert 'Outside the trades' not in report
    assert 'individually reconciled team snapshots' in report
    assert 'entire league' in report
    assert audit_publication(research, report)['status'] == 'pass'
    old = report.replace('These players belong to individually reconciled team snapshots, not the entire league; game-by-game fantasy eligibility remains unverified.',
                         'These NHL totals reconcile with the team scoring snapshots; game-by-game eligibility has not independently been confirmed.')
    assert 'unqualified_partial_scoring_attribution' in audit_publication(research, old)['issues']


def test_scoring_diagnostics_do_not_upgrade_partial_or_invent_cause():
    rows = [{'status': 'reconciled', 'numeric_match': True, 'identity_complete': True,
             'team_id': 'ok', 'team_name': 'Matched'},
            {'status': 'discrepancy', 'difference': -2, 'numeric_match': False,
             'identity_complete': True, 'team_id': 'diff', 'team_name': 'Difference',
             'active_ids_without_nhl_game_rows': ['p1']},
            {'status': 'reconciled_with_identity_gaps', 'difference': 0,
             'numeric_match': True, 'identity_complete': False,
             'unmatched_active_ids': ['p3'], 'team_id': 'gap', 'team_name': 'Identity Gap'}]
    coverage = summarize_attribution_coverage({'period': 6, 'teams': rows})
    assert coverage['status'] == 'partial'
    assert (coverage['team_count'], coverage['reconciled_teams']) == (3, 1)
    assert coverage['point_discrepancy_teams'] == 1
    assert coverage['identity_gap_teams'] == 1
    assert coverage['exceptions'][0]['difference'] == -2
