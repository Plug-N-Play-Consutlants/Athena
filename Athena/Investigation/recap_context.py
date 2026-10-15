"""Bounded, read-only recap context from canonical artifacts.

A current roster snapshot is NOT evidence of the lineup during a past scoring
period.  Prior-season production is NOT period production.  Draft ownership is
reported only with explicit source provenance and no assumed trade motivation.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path


def _load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, UnicodeError):
        return None


def _season_year(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number // 10000 if number > 10000 else number


def reconcile_recap_context(output, *, active_season=None, selected_period=None, teams=None):
    root = Path(output)
    roster = _load(root / "player_pool_master.json")
    production = _load(root / "player_production.json")
    draft = _load(root / "draft_picks.json")
    result = {"roster": {"status": "not_available"}, "production": {"status": "not_available"},
              "injuries": {"status": "not_available"}, "draft_assets": {"status": "not_available"},
              "period": selected_period}
    allowed = set(teams or [])
    if isinstance(roster, dict) and isinstance(roster.get("records"), list):
        records = [r for r in roster["records"] if isinstance(r, dict)]
        source_season = _season_year(roster.get("active_season"))
        expected = _season_year(active_season)
        season_ok = expected is not None and source_season == expected
        team_counts = defaultdict(lambda: {"rostered": 0, "active": 0, "reserve": 0, "injured_reserve": 0})
        injured = defaultdict(list)
        for r in records:
            name = r.get("fantasy_team")
            if not name or (allowed and name not in allowed):
                continue
            slot = str(r.get("roster_slot") or "").lower()
            team_counts[name]["rostered"] += 1
            if slot in ("active", "reserve", "injured_reserve"):
                team_counts[name][slot] += 1
            if slot == "injured_reserve" and r.get("player_name"):
                injured[name].append(str(r["player_name"]))
        result["roster"] = {"status": "current_snapshot_context_only" if season_ok else "season_unverified",
            "fetched_at": roster.get("fetched_at"), "source_season": source_season,
            "expected_season": expected, "player_count": len(records), "teams": dict(team_counts),
            "period_lineup_verified": False}
        result["injuries"] = {"status": "roster_ir_only_not_medical_verification" if season_ok else "season_unverified",
            "teams": dict(injured), "period_injury_verified": False,
            "note": "IR placement is a roster designation, not a verified diagnosis or past-week status."}
    if isinstance(production, list):
        seasons = sorted({str(r.get("season")) for r in production if isinstance(r, dict) and r.get("season")})
        result["production"] = {"status": "historical_or_season_totals_only", "record_count": len(production),
            "seasons": seasons, "period_production_verified": False,
            "note": "Season totals cannot be attributed to a specific scoring period."}
    if isinstance(draft, dict):
        expected = _season_year(active_season)
        season_ok = expected is not None and _season_year(draft.get("season")) == expected
        future = draft.get("future_draft_assets") or {}
        picks = future.get("picks") if isinstance(future, dict) else None
        by_team = defaultdict(lambda: Counter())
        if isinstance(picks, list):
            for p in picks:
                if not isinstance(p, dict) or p.get("ownership_status") not in ("retained", "traded", "current_owner_confirmed"):
                    continue
                owner = p.get("current_owner") or {}
                name = owner.get("team_name") if isinstance(owner, dict) else None
                year = p.get("year")
                if name and (not allowed or name in allowed) and isinstance(year, int):
                    by_team[name][year] += 1
        result["draft_assets"] = {"status": "future_ownership_snapshot" if season_ok else "season_unverified",
            "source_season": draft.get("season"), "teams": {t: dict(c) for t,c in by_team.items()},
            "period_trade_link_verified": False, "pick_count": len(picks) if isinstance(picks, list) else 0}
    return result
