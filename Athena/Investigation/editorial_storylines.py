"""Athena-owned, source-verified cross-period editorial signals.

A two-week trend requires *three* complete, stable-ID cumulative standings
snapshots from one season and league. Missing history is a gap, never a streak.
"""
from __future__ import annotations

from pathlib import Path
from Athena.Investigation.standings_archive import load_snapshot


def investigate_storyline_continuity(output_dir: Path, league_id: str | None,
                                    season: int | str | None, period: int | None) -> dict:
    if not league_id or not season or type(period) is not int or period < 3:
        return {"status": "insufficient_period_history", "signals": []}
    try:
        windows = [load_snapshot(output_dir, str(league_id), season, w)
                   for w in (period - 2, period - 1, period)]
    except (ValueError, TypeError, KeyError, OSError):
        return {"status": "insufficient_period_history", "signals": []}
    observations = []
    for snap in windows:
        teams = {str(row["team_id"]): row for row in snap["teams"]}
        observations.append(teams)
    ids = [set(rows) for rows in observations]
    if not (ids[0] == ids[1] == ids[2]):
        return {"status": "identity_membership_changed", "signals": []}
    signals = []
    for tid in sorted(ids[0]):
        before, middle, now = (s[tid] for s in observations)
        moves = (before["rank"] - middle["rank"], middle["rank"] - now["rank"])
        if moves[0] * moves[1] <= 0:
            continue
        signals.append({"team_id": tid, "team_name": str(now.get("name") or tid),
                        "periods": [period - 2, period - 1, period],
                        "direction": "climb" if moves[0] > 0 else "slide",
                        "movements": list(moves), "overall_rank_change": sum(moves),
                        "rank": now["rank"], "source": "canonical_period_standings"})
    signals.sort(key=lambda signal: (-abs(signal["overall_rank_change"]), signal["team_id"]))
    return {"status": "verified" if signals else "no_consecutive_direction",
            "source": "canonical_period_standings", "periods": [period - 2, period - 1, period],
            "signals": signals}
