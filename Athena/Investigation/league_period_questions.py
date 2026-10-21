"""Evidence-bounded direct period inquiries for the named fantasy league."""
from __future__ import annotations


def answer_league_period_question(ctx, question: str, route: str) -> dict:
    from Scout.conversation.responses import response, developer_info
    from Athena.Investigation.standings_acquisition import resolve_league_context
    from Athena.Investigation.league_recap import resolve_archived_period
    from Core.project_paths import OUTPUT_DIR
    trace = {'schema': 1, 'selected_route': route, 'route_reason': 'explicit_league_period_inquiry',
             'source_attempts': [], 'rejected_evidence': [], 'terminal_reason': None}
    try:
        league, season = resolve_league_context(ctx.league_profile, ctx.standings_archive)
    except (ValueError, AttributeError, TypeError):
        league, season = None, None
    trace['source_attempts'].append({'source': 'league_context', 'status': 'resolved' if league and season else 'unresolved'})
    period = resolve_archived_period(OUTPUT_DIR, league, season) if league and season else None
    trace['source_attempts'].append({'source': 'standings_archive', 'status': 'available' if period is not None else 'unavailable'})
    evidence = {'league_id_present': bool(league), 'season_present': bool(season),
                'latest_archived_period': period, 'archive_is_completion_proof': False}
    if route == 'league_scoring_period_boundary':
        trace['rejected_evidence'].append({'source': 'standings_archive', 'reason': 'not_scoring_period_finalization_proof'})
        trace['rejected_evidence'].append({'source': 'roster_calendar', 'reason': 'not_scoring_period_boundary_proof'})
        trace['terminal_reason'] = 'verified_scoring_period_schedule_unavailable'
        # Archived standings and roster-calendar dates cannot independently
        # establish when a scoring period ended or that it was finalized.
        conclusion = ('The most recently completed JHLPAA scoring period is not independently verified. '
                      + (f'Period {period} is the latest available standings archive, but an archive is not proof that scoring closed. ' if period is not None else 'No usable scoring-period archive is established. ')
                      + 'Fantrax roster-period dates must not be presented as scoring-period boundaries.')
        missing = ['verified_scoring_period_dates', 'scoring_period_finalization']
    else:
        from Athena.Investigation.period_evidence_acquisition import acquire_player_period_production
        production = acquire_player_period_production(league_id=league, season=season, period=period)
        trace['source_attempts'].append({'source': 'fantrax_player_stats', 'status': production.get('status'),
                                         'attempted': bool(production.get('attempted')),
                                         'verified': bool(production.get('verified'))})
        evidence['player_production'] = {k: production.get(k) for k in ('status','attempted','verified','period','reason','diagnostic','schema_inspection')}
        records = production.get('records') or []
        # Do not rank ambiguous period data, and do not confuse Fantrax FPts
        # with this league's goals-plus-assists scoring contract.
        if production.get('verified') and records:
            trace['terminal_reason'] = 'ranking_identity_and_fields_not_validated'
            conclusion = (f'Fantrax returned {len(records)} verified period-attributed records for period {period}, '
                          'but a trustworthy top-ten G+A ranking still requires validated player identities and scoring fields.')
        else:
            trace['rejected_evidence'].append({'source': 'fantrax_player_stats', 'reason': production.get('status')})
            trace['terminal_reason'] = 'period_player_production_not_verified'
            conclusion = (f'A verified top-ten JHLPAA player G+A ranking for scoring period {period} is not available. '
                          f'Fantrax acquisition status: {production.get("status")}; {production.get("reason")}. '
                          'Season-to-date totals, fantasy points, and current roster snapshots are not substitutes for period G+A.')
        missing = ['verified_player_period_g_plus_a', 'verified_scoring_period']
    evidence['decision_trace'] = trace
    return response(intent=route, title=('JHLPAA scoring period verification' if route == 'league_scoring_period_boundary' else 'JHLPAA player period leaders'),
                    engine_conclusion=conclusion, natural_language_response=conclusion,
                    observed_facts=[], known_limitations=missing, confidence=.3,
                    developer=developer_info(route, getattr(ctx,'files_loaded',[]),
                                             knowledge_used=['fantrax_period_evidence'],
                                             intelligence_used=['period_scope_validation'],
                                             missing=missing, files_read=[]),
                    ) | {'period_investigation': evidence}
