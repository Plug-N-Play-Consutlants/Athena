"""Scout-owned narrative: consumes analytical findings; does not investigate."""

def _points(value):
    return f"{value:g}" if isinstance(value, (int, float)) else "unverified"


def _describe(f):
    kind, team = f["kind"], f.get("team")
    change, rank, points = f.get("rank_change"), f.get("rank"), f.get("period_points")
    movement = f"{abs(change)} {'place' if abs(change) == 1 else 'places'}" if isinstance(change, int) else ""
    if kind == "trade_cluster":
        exchanges = []
        for exchange in f.get("exchanges", []):
            exchanges.append("; ".join(f"{club} acquired {', '.join(assets)}" for club, assets in exchange.get("received", {}).items() if assets))
        return f"{team} completed {f['trade_count']} separate trades, making it the week's busiest trading team. " + " ".join(exchanges) + ". The exchanges are confirmed; their competitive impact remains to be seen."
    if kind == "trade":
        return f"The league recorded {f['trade_count']} trades this period. Their competitive impact remains to be established."
    if kind == "surge":
        return f"{team} put up {_points(points)} points, {'the highest verified total' if f.get('top_score') else 'one of the top totals'} of the week, and climbed {movement} to rank {rank}."
    if kind == "scoring_leader":
        return f"{team} posted {_points(points)} points, among the week's leading performances."
    if kind == "slide":
        return f"{team} slipped {movement} to rank {rank}, with {_points(points)} points this week. The scoring record alone doesn't explain the cause."
    if kind == "climb":
        return f"{team} moved up {movement} to rank {rank}, scoring {_points(points)} points."
    if kind == "secondary_market":
        examples = "; ".join(f.get("examples", []))
        return f"Beyond the trades, {f['transaction_count']} other transactions were recorded." + (f" For example: {examples}." if examples else "")
    if kind == "market":
        return f"The league recorded {f['transaction_count']} transactions in the selected period."
    if kind == "quiet_success":
        return f"{team} scored {_points(points)} points without a recorded transaction across the two observed weeks. Sometimes the scoreboard does the talking."
    if kind == "quiet_watch":
        names = ", ".join(f.get("teams", [])[:3])
        return f"No transactions were recorded for {names}{' and others' if len(f.get('teams', [])) > 3 else ''} across the two observed weeks. Who makes the next move?"
    raise ValueError(f"Unsupported Athena research finding: {kind}")


def compose_period_report(*, research):
    if research.get("schema") != "athena.league_period_research.v2":
        raise ValueError("Scout requires Athena structured research contract v2")
    label = f"Week {research['period']}" if research.get("period") else "recent activity"
    lines = [f"{research['league_name']} | {label}"]
    findings = research.get("findings") or []
    if not findings:
        return "\n\n".join(lines + ["There isn't enough verified evidence to identify a league-wide development yet."])
    lead = findings[0]
    lines.extend(["The week's defining development", _describe(lead)])
    primary = [f for f in findings[1:] if f["kind"] not in ("secondary_market", "market", "quiet_watch", "quiet_success")]
    if primary:
        lines.append("Around the league")
        lines.extend(_describe(f) for f in primary)
    market = [f for f in findings if f["kind"] in ("secondary_market", "market")]
    if market:
        lines.append("On the transaction wire")
        lines.extend(_describe(f) for f in market)
    quiet = [f for f in findings if f["kind"] in ("quiet_success", "quiet_watch")]
    if quiet:
        lines.append("Who's keeping quiet?")
        lines.extend(_describe(f) for f in quiet)
    rows = research.get("comparison", {}).get("teams", [])
    ranks = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("rank"), int):
            ranks.setdefault(row["rank"], set()).add(str(row.get("name") or row.get("team_id")))
    tied = {rank: names for rank, names in ranks.items() if len(names) > 1}
    if tied:
        lines.append("Standings note")
        lines.append("The archive shows shared ranks: " + "; ".join(f"{rank}: {', '.join(sorted(names))}" for rank, names in sorted(tied.items())) + ". No tiebreak is assumed.")
    lines.append("What to watch")
    lines.append("Next week's results will help show which moves stick. Player-level contributions and trade impact still require verified period-specific evidence.")
    return "\n\n".join(lines)
