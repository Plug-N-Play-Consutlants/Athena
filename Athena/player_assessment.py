"""Evidence-bound current, legacy and career-stage player assessment.

NHL evidence provides observations; Athena draws independent, dated conclusions.
The same rules apply to every player, regardless of identity or seed profile.
"""
from __future__ import annotations
from typing import Any

from Knowledge.Intelligence.Public.player_evidence import authoritative_statistical_view

LABELS = ("Franchise Superstar", "Star", "Core Player", "Role Player", "Depth Player")


def _rate(position: str, points: float, games: float) -> str:
    if not games or position == "G":
        return ""
    rate = points / games
    thresholds = (0.95, 0.72, 0.48, 0.25) if position == "D" else (1.35, 1.0, 0.65, 0.32)
    return next((label for label, threshold in zip(LABELS, thresholds) if rate >= threshold), LABELS[-1])


def assess_player(evidence: dict[str, Any]) -> dict[str, Any]:
    authoritative = authoritative_statistical_view(evidence, window_size=3)
    rows = authoritative["season_series"]
    recent = authoritative["recent_window"]
    try:
        target_start = int(str(authoritative.get("target_season") or (rows[0]["season"] if rows else ""))[:4]) if rows else 0
    except ValueError:
        target_start = 0
    games = sum(row["gp"] for row in recent)
    points = sum(row["points"] for row in recent)
    position = str(evidence.get("position") or "")
    try:
        latest_start = int(str(recent[0]["season"])[:4]) if recent else 0
        stale = latest_start < target_start - 1
    except ValueError:
        stale = False
    current = _rate(position, points, games) if games >= 40 and not stale else ""
    rates = [row["points"] / row["gp"] for row in recent]
    trend = "Insufficient seasons for a trend"
    limited_latest = bool(recent and recent[0]["gp"] < 30)
    if len(rates) == 3 and not stale and not limited_latest:
        baseline = (recent[1]["points"] + recent[2]["points"]) / (recent[1]["gp"] + recent[2]["gp"])
        delta = rates[0] - baseline
        trend = "Rising" if delta >= 0.15 else "Declining" if delta <= -0.15 else "Broadly stable"

    career = authoritative["career"]
    career_games = career.get("games")
    career_points = career.get("points")
    career_goals = career.get("goals")
    legacy = ""
    if isinstance(career_games, (int, float)) and career_games >= 150 and isinstance(career_points, (int, float)):
        career_rate = career_points / career_games
        if career_games >= 500 and (career_rate >= (0.72 if position == "D" else 1.1)
                                   or position != "D" and isinstance(career_goals, (int, float)) and career_goals / career_games >= .55):
            legacy = "Career Superstar"
        elif career_games >= 300 and career_rate >= (0.45 if position == "D" else .8):
            legacy = "Career Star"
        elif career_games >= 500:
            legacy = "Established Career"

    age = evidence.get("age")
    seasons = len(rows)
    stage = ""
    if seasons == 0:
        stage = "Prospect" if evidence.get("verified_prospect") else ""
    elif not stale and seasons == 1 and isinstance(career_games, (int, float)) and career_games <= 82:
        stage = "Rookie"
    elif isinstance(age, int) and age >= 35 and seasons >= 3:
        stage = "Late Career Veteran"
    elif isinstance(age, int) and age >= 30 and seasons >= 3:
        stage = "Veteran"
    elif seasons < 3:
        stage = "Emerging NHL Player"
    else:
        stage = "Established NHL Player"

    awards = [row for row in evidence.get("awards", []) if isinstance(row, dict) and row.get("trophy")]
    return {
        "current_tier": current,
        "career_legacy": legacy,
        "career_stage": stage,
        "rookie_tags": ["Development Potential", "Early NHL Career"] if stage == "Rookie" else [],
        "as_of_season": recent[0].get("season", "") if recent else "",
        "window_seasons": [row["season"] for row in recent],
        "seasons_used": len(recent),
        "recent_games": games,
        "recent_points": points,
        "trend": trend,
        "trend_provisional": len(recent) < 3 or stale or limited_latest,
        "awards": awards,
        "limitations": (["Most recent NHL season is too old for a current rating; historical production is retained."] if stale else
                        (["Current tier is a scoring-based estimate; injury, deployment and defensive impact require separate evidence."]
                         if current else []) +
                        (["Latest season has a limited game sample; trend remains provisional."] if limited_latest else
                         ["A three-season trend is not yet available."] if len(recent) < 3 else [])),
        "source": authoritative.get("source") or evidence.get("source", ""),
        "evidence_authority": authoritative["authority"],
    }


def assessment_copy(name: str, evidence: dict[str, Any], assessment: dict[str, Any]) -> str:
    """Explain evidence and separate present contribution from earned legacy."""
    seasons = assessment["seasons_used"]
    current = assessment["current_tier"]
    window = ", ".join(assessment["window_seasons"])
    if current:
        opening = (f"Across {seasons} NHL regular season{'s' if seasons != 1 else ''} "
                   f"({window}), {name} recorded {assessment['recent_points']} points in "
                   f"{assessment['recent_games']} games. Athena currently estimates a {current.lower()} "
                   f"scoring tier from that window. The trend is {assessment['trend'].lower()}.")
    else:
        opening = f"Athena does not have enough comparable NHL regular-season evidence to rate {name}'s current contribution."
    if assessment["trend_provisional"]:
        opening += " The trend remains provisional because season coverage or comparability is limited."
    legacy = assessment["career_legacy"]
    if legacy:
        second = (f"Career legacy is assessed separately: {legacy.lower()} from "
                  f"{evidence['career_points']} points in {evidence['career_games']} NHL games.")
    else:
        second = "Career legacy remains unclassified until a sufficient NHL career record is attached."
    awards = assessment.get("awards") or []
    if awards:
        second += " NHL-recorded honours include " + ", ".join(
            f"{item['trophy']} ({item['count']})" for item in awards[:4]) + "."
    return opening + "\n\n" + second
