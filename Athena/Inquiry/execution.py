"""Adaptive inquiry execution helpers.

These helpers turn a resolved inquiry into bounded next-pass analysis. They do
not invent missing evidence. Instead they distinguish evidence that blocks a
conclusion from evidence that merely limits how specific the construction can
be, then execute the reasoning that remains possible.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List


def construct_transaction_paths(*, team_name: str, target_name: str,
                                protected_assets: Iterable[str] = (),
                                cap_waived: bool = False,
                                acquisition_price_known: bool = False) -> Dict[str, Any]:
    protected = [str(x) for x in protected_assets if str(x).strip()]
    protected_text = ", ".join(protected)
    keep_clause = f"Keep {protected_text} outside the package and " if protected_text else ""
    protected_conclusion = f" without moving {protected_text}" if protected_text else ""
    paths = [
        {
            "label": "Direct two-team construction",
            "analysis": (
                f"{keep_clause}build the return around the strongest available non-protected "
                "NHL roster asset, premium prospect capital and high draft capital. For a player of this class, secondary pieces "
                "cannot substitute for a genuine centerpiece; Athena should reject quantity-only packages."
            ),
        },
        {
            "label": "Three-team value conversion",
            "analysis": (
                f"If {team_name}'s best movable asset is a poor fit for the selling club, route that asset to a third team and send "
                "the resulting younger roster value, prospects or picks to the seller. The third team must solve a value/fit problem, "
                "not exist merely to make the diagram more complicated."
            ),
        },
        {
            "label": "Timing/control construction",
            "analysis": (
                "If the current acquisition price is prohibitive, the viable path is to preserve the protected core and accumulate or "
                "convert future assets until the seller's leverage or the player's contractual timeline changes. This is a construction "
                "path, not evidence that such a market change will occur."
            ),
        },
    ]
    conclusion = (
        f"A {target_name} acquisition can be constructed{protected_conclusion}, but the evidence currently supports package "
        "architecture rather than a defensible named offer. "
    )
    if cap_waived:
        conclusion += "With salary-cap feasibility waived, the central problem is acquisition value and seller fit rather than cap matching. "
    else:
        conclusion += "In the real-world frame, any value construction must also survive cap/CBA execution; the current incomplete team ledger prevents that final mechanical determination. "
    if not acquisition_price_known:
        conclusion += "Because verified acquisition-price/counterparty evidence is missing, Athena should not pretend a specific package is sufficient."
    return {"conclusion": conclusion, "paths": paths, "protected_assets": protected,
            "cap_waived": cap_waived, "acquisition_price_known": acquisition_price_known}


def _parse_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    candidates = [text, text.replace("Z", "+00:00")]
    for candidate in candidates:
        try:
            dt = datetime.fromisoformat(candidate)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %I:%M %p", "%a %b %d, %Y, %I:%M%p", "%a %b %d, %Y, %I:%M %p"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def _record_assets(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [x for x in (record.get("assets") or []) if isinstance(x, dict)]


def summarize_recent_league_activity(transaction_history: Dict[str, Any], *, days: int = 7,
                                     now: datetime | None = None,
                                     period: str | int | None = None,
                                     period_bounds: dict | None = None,
                                     allow_rolling: bool = True) -> Dict[str, Any]:
    """Build a time-scoped league activity read from canonical transactions."""
    records = [x for x in ((transaction_history or {}).get("records") or []) if isinstance(x, dict)]
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    cutoff = now - timedelta(days=max(1, days))
    scoped = []
    undated = []
    for row in records:
        dt = _parse_time(row.get("timestamp"))
        if dt is None:
            undated.append(row)
        elif cutoff <= dt.astimezone(timezone.utc) <= now.astimezone(timezone.utc):
            scoped.append(row)
    # Explicit league period membership takes precedence when the caller supplies
    # a resolved period. Calendar time is not a substitute for a lineup-lock boundary.
    if period is not None:
        period_text = str(period).strip()
        # Explicit provider period wins. Timestamp-only rows may be attributed
        # to the single verified reporting window; no rolling-week substitution.
        start = (period_bounds or {}).get("start")
        end = (period_bounds or {}).get("end")
        scoped = []
        for r in records:
            label = r.get("period") or r.get("season_week")
            if label is not None and str(label).strip():
                if str(label).strip() == period_text:
                    scoped.append(r)
            elif start and end:
                dt = _parse_time(r.get("timestamp"))
                if dt is not None and start <= dt.date().isoformat() <= end:
                    scoped.append(r)
    # If canonical rows carry explicit season-week semantics but timestamps are
    # unavailable, use the latest observed week as a bounded fallback.
    if period is None and allow_rolling and not scoped and records and undated:
        weeks = [str(r.get("season_week") or "") for r in records if str(r.get("season_week") or "")]
        if weeks:
            latest = sorted(set(weeks))[-1]
            scoped = [r for r in records if str(r.get("season_week") or "") == latest]
    if period is None and not allow_rolling:
        scoped = []
    type_counts: Dict[str, int] = {}
    teams = set()
    ranked = []
    for row in scoped:
        kind = str(row.get("transaction_type") or "unknown")
        type_counts[kind] = type_counts.get(kind, 0) + 1
        participants = [p for p in (row.get("participants") or []) if isinstance(p, dict)]
        for p in participants:
            name = str(p.get("participant_id") or p.get("team_id") or p.get("participant_name") or p.get("team_name") or p.get("manager_name") or p.get("name") or "").strip()
            if name: teams.add(name)
        for key in ("team_id", "from_team", "to_team") if not participants else ():
            name = str(row.get(key) or "").strip()
            if name: teams.add(name)
        if not participants and not row.get("team_id"):
            name = str(row.get("team_name") or row.get("manager_name") or "").strip()
            if name: teams.add(name)
        assets = _record_assets(row)
        picks = sum(1 for a in assets if str(a.get("asset_type") or "").lower() in {"draft_pick", "pick"})
        players = sum(1 for a in assets if str(a.get("asset_type") or "").lower() == "player")
        is_trade = "trade" in kind.lower() or len(participants) > 1
        score = (20 if is_trade else 0) + picks * 4 + players * 2 + len(assets)
        ranked.append((score, row))
    ranked.sort(key=lambda x: (x[0], str(x[1].get("timestamp") or "")), reverse=True)
    highlights = []
    for score, row in ranked[:5]:
        summary = str(row.get("summary") or "").strip()
        if not summary:
            assets = [str(a.get("asset_name") or "").strip() for a in _record_assets(row) if str(a.get("asset_name") or "").strip()]
            kind = str(row.get("transaction_type") or "Transaction").replace("_", " ").title()
            summary = kind + (": " + ", ".join(assets[:8]) if assets else "")
        if (not summary or summary.casefold() in {"trade completed", "trade", "transaction completed"}) and _record_assets(row):
            named = [str(a.get("asset_name") or a.get("name") or "").strip() for a in _record_assets(row)]
            named = [x for x in named if x]
            if named:
                summary = (summary or "Trade") + ": " + ", ".join(named[:10])
        highlights.append({"significance_score": score, "summary": summary,
                           "participants": row.get("participants") or [], "assets": _record_assets(row),
                           "transaction_id": row.get("transaction_id"),
                           "transaction_type": row.get("transaction_type"), "timestamp": row.get("timestamp"), "season_week": row.get("season_week")})
    return {"period_days": days, "transaction_count": len(scoped), "team_count": len(teams),
            "transaction_types": type_counts, "highlights": highlights,
            "source_record_count": len(records), "timestamp_coverage": len(records) - len(undated),
            "scope_method": ("period_label_or_shared_bounds" if period_bounds and period is not None
                              else "explicit_period" if period is not None
                              else "rolling_calendar_window" if allow_rolling
                              else "unresolved_period")}


def reconstruct_league_trade(transaction_history: Dict[str, Any], *, team_names: Iterable[str] = (),
                             player_names: Iterable[str] = ()) -> Dict[str, Any]:
    """Retrieve whole canonical trade events, never infer a deal from draft-board ownership."""
    teams = [str(n).casefold() for n in team_names if str(n).strip()]
    players = [str(n).casefold() for n in player_names if str(n).strip()]
    matches = []
    for row in (transaction_history or {}).get("records", []):
        if not isinstance(row, dict) or "trade" not in str(row.get("transaction_type") or "").lower():
            continue
        names = [str(p.get("participant_name") or p.get("team_name") or "") for p in row.get("participants", []) if isinstance(p, dict)]
        asset_names = [str(a.get("asset_name") or "") for a in _record_assets(row)]
        team_hits = sum(any(t in n.casefold() for n in names) for t in teams)
        player_hits = sum(any(t in n.casefold() for n in asset_names) for t in players)
        if (teams and team_hits < len(teams)) or (players and player_hits == 0) or (not teams and not players):
            continue
        matches.append({"record": row, "team_hits": team_hits, "player_hits": player_hits,
                        "score": team_hits * 3 + player_hits})
    matches.sort(key=lambda m: m["score"], reverse=True)
    return {"matches": matches, "matched_count": len(matches)}
