"""Athena-owned canonical league standings investigation.

Scout supplies context and renders findings. Provider construction, archival
acquisition, period resolution, and comparison never belong to presentation.
"""
from __future__ import annotations
import re
from typing import Any
from pathlib import Path


def investigate_period_standings(ctx: Any, question: str) -> dict:
    from Core.project_paths import OUTPUT_DIR
    from Athena.Investigation.standings_archive import compare_archived
    from Athena.Investigation.standings_acquisition import resolve_league_context, ensure_period_snapshots
    periods = [int(n) for pair in re.findall(r"\bweeks?\s*(\d+)\b|\band\s*(\d+)\b", question, re.I) for n in pair if n]
    range_match = re.search(r"\bweeks?\s*(\d+)\s*(?:-|to|through)\s*(\d+)", question, re.I)
    if range_match:
        start, end = map(int, range_match.groups())
        if 1 <= start <= end <= 60:
            periods = list(range(start, end + 1))
    periods = sorted(set(periods))
    # A season-to-date question supplies a temporal scope, even without a
    # numbered week. Discover the latest validated archived period rather than
    # pretending the user omitted the scope. Do not infer an unobserved period.
    season_to_date = bool(re.search(r"\b(since the start of (?:the )?season|season.to.date|this season|so far this season)\b", question, re.I))
    archive = ctx.standings_archive or {}
    context_error = None
    try:
        league_id, season = resolve_league_context(ctx.league_profile, archive)
    except ValueError as exc:
        league_id, season, context_error = None, None, str(exc)
    if not periods and season_to_date and league_id and season:
        folder = Path(OUTPUT_DIR) / 'Standings' / str(league_id) / str(season)
        from Athena.Investigation.standings_archive import load_snapshot
        valid = []
        for path in folder.glob('period_*.json'):
            try:
                period = int(path.stem.split('_')[-1])
                load_snapshot(OUTPUT_DIR, str(league_id), season, period)
                valid.append(period)
            except (ValueError, OSError, KeyError, TypeError, __import__('json').JSONDecodeError):
                continue
        if valid:
            periods = [max(valid)]
    acquisition = None
    if periods and league_id and season:
        fetcher = None
        try:
            from Providers.Fantrax.fantrax_client import FantraxClient
            client = FantraxClient(league_id=league_id, season=season)
            if client.has_cookie_auth():
                fetcher = client.get_standings
        except (ImportError, ValueError, OSError):
            pass
        acquisition = ensure_period_snapshots(
            OUTPUT_DIR, league_id=league_id, season=season, period=max(periods),
            expected_teams=(ctx.league_profile or {}).get('team_count'),
            season_to_date=season_to_date or len(periods) > 2 or min(periods) < max(periods)-1,
            fetch=fetcher)
    facts, limitations, comparison = [], [], None
    if not periods:
        limitations.append('No validated current period could be resolved from the standings archive; current Fantrax period discovery or acquisition is required.')
    if not league_id or not season:
        limitations.append(f'Canonical league context is unavailable: {context_error}.')
    if periods and league_id and season:
        target = max(periods)
        comparison = compare_archived(OUTPUT_DIR, str(league_id), season, target,
            season_to_date=season_to_date or len(periods) > 2 or min(periods) < target - 1)
        if comparison.get('status') == 'compared':
            for row in sorted(comparison['teams'], key=lambda r: r['rank']):
                movement = row.get('rank_change')
                movement_text = f'{movement:+d} places' if movement is not None else 'baseline unavailable'
                points = row.get('period_points')
                scoring = f'{points:g} period points' if type(points) in (int, float) else 'period scoring unavailable'
                facts.append(f"{row.get('name') or row['team_id']}: rank {row['rank']}, {movement_text}, {scoring}.")
        else:
            missing = comparison.get('missing_periods') or []
            limitations.append(f'Canonical standings for the requested comparison are unavailable (missing periods: {missing}); no rankings or movement have been inferred.')
    if acquisition is not None and acquisition.get('missing_periods'):
        limitations.append('Authenticated Fantrax standings acquisition is incomplete: ' + '; '.join(
            f"period {p}: {acquisition['errors'][p]}" for p in acquisition['missing_periods']))
    return {'periods': periods, 'facts': facts, 'limitations': limitations,
            'acquisition': acquisition, 'comparison': comparison,
            'state': 'evidence_available' if facts else 'evidence_unavailable'}
