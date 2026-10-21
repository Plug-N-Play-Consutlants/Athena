"""Evidence-grounded league editorial investigation; no inferred standings or motives."""
from collections import Counter


def _name(asset):
    return str(asset.get("asset_name") or asset.get("name") or "unnamed asset")


def _movements(row):
    sides = {}
    unresolved = []
    for asset in row.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        context = asset.get("movement_context") or {}
        source = str(context.get("from_team_name") or "").strip()
        destination = str(context.get("to_team_name") or "").strip()
        if source and destination and source != destination:
            sides.setdefault(destination, []).append(_name(asset))
        else:
            unresolved.append(_name(asset))
    return sides, unresolved


def investigate_league_period(transaction_history, period, *, period_bounds=None):
    """Return defensible narratives from canonical transaction rows for one week."""
    from Athena.Inquiry.execution import _parse_time
    start, end = (period_bounds or {}).get("start"), (period_bounds or {}).get("end")
    records = []
    for r in (transaction_history or {}).get("records", []):
        if not isinstance(r, dict):
            continue
        label = r.get("period") or r.get("season_week")
        if label is not None and str(label).strip():
            if str(label).strip() == str(period):
                records.append(r)
        elif start and end:
            dt = _parse_time(r.get("timestamp"))
            if dt is not None and start <= dt.date().isoformat() <= end:
                records.append(r)
    trades = [r for r in records if "trade" in str(r.get("transaction_type") or "").lower()]
    trade_teams = Counter()
    stories = []
    for row in trades:
        participants = [str(p.get("participant_name") or p.get("team_name") or "") for p in row.get("participants") or [] if isinstance(p, dict)]
        trade_teams.update(set(n for n in participants if n))
        received, unresolved = _movements(row)
        if received:
            details = "; ".join(f"{team} received {', '.join(names)}" for team, names in sorted(received.items()))
            lead = "Trade: " + details + "."
        else:
            lead = "Trade recorded between " + " and ".join(participants) + "; player destinations unverified."
        stories.append({"type":"trade", "transaction_id":row.get("transaction_id"), "lead":lead,
                        "participants":participants, "received":received, "unresolved_assets":unresolved,
                        "interpretation":"The exchange changes roster composition; whether it improves either side requires scoring, roster and keeper context."})
    multi = [(team, n) for team,n in trade_teams.most_common() if n > 1]
    if multi:
        team, count = multi[0]
        headline = f"{team} at the center of Week {period}'s trading"
        opening = f"{team} appears in {count} separate completed trades in the canonical Week {period} record. That concentration makes its roster reshaping the leading transaction story, although management intent and competitive outcome are not established."
    elif stories:
        headline = f"Week {period}: trades reshape the league"
        opening = f"Week {period} contains {len(stories)} completed trade events. Their importance lies in the specific roster exchanges, not merely the number of transaction rows."
    else:
        headline = f"Week {period}: league activity under review"
        opening = "No completed trade events are verified for this period in the available canonical transaction record."
    other = [r for r in records if r not in trades]
    moves = []
    for row in other:
        summary = str(row.get("summary") or "").strip()
        if summary: moves.append({"summary":summary, "transaction_id":row.get("transaction_id"),"type":row.get("transaction_type")})
    return {"headline":headline,"opening":opening,"trades":stories,"other_moves":moves,
            "trade_count":len(trades),"record_count":len(records),"multiple_trade_teams":multi,
            "missing_evidence":["Period standings and prior-period movement", "Week-specific player scoring and deployment", "Team roster construction and keeper priorities"],
            "evidence_boundary":"Trade directions and recorded acquisitions are facts; motivations, winners and standings impact remain hypotheses."}


def compose_league_editorial(editorial, period):
    """Compose an evidence-bounded article from an investigation, not a transaction dump.

    Section boundaries are explicit because Scout's lightweight renderer displays
    each line as a separate paragraph; unsupported league claims are not inferred.
    """
    sections = [
        editorial.get("headline", f"Week {period}: league activity"),
        "",
        editorial.get("opening", ""),
    ]
    if editorial.get("trades"):
        sections += ["", "The major exchanges"]
        for story in editorial["trades"]:
            sections += ["", story["lead"], story["interpretation"]]
    other = editorial.get("other_moves") or []
    if other:
        sections += ["", "Elsewhere around the league"]
        # Secondary activity is reported as recorded, not promoted to a
        # performance-based ranking without the required scoring evidence.
        sections += [move["summary"] for move in other[:5] if move.get("summary")]
    sections += ["", "What remains unresolved",
        "Standings movement, player production and keeper implications have not yet been reconciled. Those are necessary before calling trade winners or identifying changes in competitive position."]
    return "\n".join(part for part in sections if part is not None)
