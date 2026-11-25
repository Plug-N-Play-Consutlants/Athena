"""Evidence-bounded team-period performance, independent of calendar finalization.

Validated cumulative standings are sufficient to report a team's weekly delta,
rank and season position. They cannot establish which rostered players earned
credit. No player contributions or ledger writes are inferred here.
"""
from __future__ import annotations
import re
import unicodedata
from pathlib import Path


def _normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(text or '').casefold())
                   if c.isalnum())


def _explicit_period(question):
    match = re.search(r'\b(?:scoring\s+)?(?:period|week)\s*(\d+)\b', question or '', re.I)
    if not match:
        return None
    period = int(match.group(1))
    return period if 1 <= period <= 60 else None


def _resolve_named_team(question, rows):
    """Require exactly one canonical team-name match, never guess from rankings."""
    q = _normalized(question)
    matches = [row for row in rows if len(_normalized(row.get('name'))) >= 4
               and _normalized(row.get('name')) in q]
    # A shorter team name embedded inside a longer one is ambiguous.
    return matches[0] if len(matches) == 1 else None


def investigate_team_performance(ctx, question, *, output=None):
    from Scout.conversation.responses import response, developer_info
    from Athena.Investigation.standings_acquisition import resolve_league_context, ensure_period_snapshots
    from Athena.Investigation.standings_archive import compare_archived, load_snapshot
    from Core.project_paths import OUTPUT_DIR
    output = Path(output) if output is not None else OUTPUT_DIR
    period = _explicit_period(question)
    facts, gaps, provenance = [], [], {'requested_period': period, 'team_resolved': False,
                                       'period_scoring_credit_verified': False,
                                       'player_credit_attempted': False, 'ledger_written': False}
    rows = []
    league = season = None
    try:
        league, season = resolve_league_context(ctx.league_profile, ctx.standings_archive)
    except (ValueError, TypeError, AttributeError):
        gaps.append('Canonical league and season context not resolved')
    if period is None:
        gaps.append('An explicit valid scoring period is required for this inquiry')
    if league and season and period is not None:
        # Try prevalidated archives first, and only fetch missing archives.
        fetch = None
        try:
            from Providers.Fantrax.fantrax_client import FantraxClient
            client = FantraxClient(league_id=league, season=season)
            if client.has_cookie_auth():
                fetch = client.get_standings
        except (ImportError, ValueError, OSError, TypeError, AttributeError):
            pass
        acquired = ensure_period_snapshots(output, league_id=league, season=season,
                                            period=period, expected_teams=(ctx.league_profile or {}).get('team_count'),
                                            fetch=fetch)
        provenance['standings_acquisition'] = {'missing_periods': acquired['missing_periods'],
                                               'available_periods': acquired['available_periods']}
        try:
            snapshot = load_snapshot(output, str(league), season, period)
            rows = snapshot['teams']
        except (OSError, ValueError, TypeError, KeyError) as exc:
            gaps.append('Requested period standings are not validated: ' + str(exc)[:160])
    team = _resolve_named_team(question, rows)
    if team is None:
        gaps.append('A single canonical named fantasy team could not be identified in the validated period archive')
        conclusion = ('I cannot identify one verified fantasy team in the requested period. '
                      'Please name the team explicitly; I will not substitute another roster or invent scoring.')
    else:
        provenance['team_resolved'] = True
        name = team['name']
        rank, total = team['rank'], team['points']
        facts.append(f'{name}: period {period} cumulative rank {rank}; cumulative points {total:g}.')
        comp = compare_archived(output, str(league), season, period)
        target = next((r for r in comp.get('teams', []) if r['team_id'] == team['team_id']), None)
        scored = target.get('period_points') if target else None
        movement = target.get('rank_change') if target else None
        lines = [f'{name} — JHLPAA scoring period {period}',
                 f'Archived cumulative standings: rank {rank}, {total:g} total points.']
        if type(scored) in (int, float):
            lines.append(f'Points earned during the period: {scored:g}.')
            facts.append(f'{name} scored {scored:g} period points (difference between validated cumulative snapshots).')
        else:
            gaps.append('Prior-period standings missing: period points cannot be derived')
        if type(movement) is int:
            lines.append(f'Standings movement: {movement:+d} places from the preceding archived period.')
            facts.append(f'{name} changed standings rank by {movement:+d} places.')
        # Compare relative to other teams only if period scores are verified by two snapshots.
        comparables = [r for r in comp.get('teams', []) if type(r.get('period_points')) in (int, float)]
        if scored is not None and len(comparables) == len(rows):
            top_score = max(r['period_points'] for r in comparables)
            leading = [r for r in comparables if r['period_points'] == top_score]
            if scored == top_score:
                lines.append('This team tied for the highest archived period total.' if len(leading) > 1
                             else 'This team led the archived period in points.')
            else:
                lines.append(f'The period-leading score was {top_score:g} points.')
        if rows:
            first = max(r['points'] for r in rows)
            if first > total:
                lines.append(f'Distance behind the cumulative points leader: {first-total:g} points.')
        lines.append('Individual contributors and underperformers cannot yet be named: historical active-lineup credit and scoring-period identity have not been independently verified. General NHL production and current roster membership are not substitutes.')
        conclusion = '\n'.join(lines)
        gaps.append('Verified historical active-lineup player credit for this scoring period is unavailable')
    return response(intent='league_team_period_performance', title='JHLPAA team period performance',
                    engine_conclusion=conclusion, natural_language_response=conclusion,
                    observed_facts=facts, known_limitations=gaps, confidence=.8 if team else .3,
                    developer=developer_info('league_team_period_performance', getattr(ctx, 'files_loaded', []),
                                              knowledge_used=['validated_cumulative_period_standings'],
                                              intelligence_used=['team_identity_resolution','period_delta_comparison'],
                                              missing=gaps, files_read=[])) | {'team_period_investigation': provenance}
