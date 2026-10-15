"""Interpret observed career records without turning correlation into causation.

This is shared Reasoning, not presentation logic. Season observations are deduplicated
by league/season/game type; competing league paths in a season are preserved.
"""
from __future__ import annotations
from collections import defaultdict
from typing import Any, Dict, List


def _number(value):
    try:
        return float(value) if value is not None and value != "" else None
    except (TypeError, ValueError):
        return None


def _season(value):
    digits = "".join(c for c in str(value or "") if c.isdigit())
    return int(digits[:4]) if len(digits) >= 4 else None


def interpret_development(history: List[Dict[str, Any]], *, age=None, birth_year=None) -> Dict[str, Any]:
    seasons = defaultdict(list)
    for event in history or []:
        if not isinstance(event, dict):
            continue
        year = _season(event.get("season"))
        league = str(event.get("league") or "").strip().upper()
        if year is None or not league:
            continue
        seasons[year].append((league, event))
    timeline = []
    for year, observations in sorted(seasons.items()):
        levels = []
        seen = set()
        for league, row in observations:
            # Some NHL feeds contain aggregate rows alongside regular/playoff rows.
            # Prefer explicit regular-season records when available.
            kind = row.get("game_type")
            if kind not in (None, 2, "2"):
                continue
            key = (league, str(row.get("team") or ""))
            if key in seen:
                continue
            seen.add(key)
            gp = _number(row.get("games_played"))
            points = _number(row.get("points"))
            if points is None:
                goals, assists = _number(row.get("goals")), _number(row.get("assists"))
                if goals is not None and assists is not None:
                    points = goals + assists
            levels.append({"league": league, "games": gp, "points": points,
                           "points_per_game": round(points / gp, 3) if gp and gp > 0 and points is not None else None})
        if levels:
            timeline.append({"season": year, "levels": levels,
                             "approximate_age": year - birth_year if isinstance(birth_year, int) else None})
    nhl = [(entry["season"], level) for entry in timeline for level in entry["levels"] if level["league"] == "NHL"]
    first_nhl = nhl[0][0] if nhl else None
    latest_nhl = nhl[-1][1] if nhl else None
    transitions = []
    for before, after in zip(timeline, timeline[1:]):
        a = {x["league"] for x in before["levels"]}
        b = {x["league"] for x in after["levels"]}
        if a != b:
            transitions.append({"from_season": before["season"], "to_season": after["season"],
                                "from_levels": sorted(a), "to_levels": sorted(b)})
    last_levels = timeline[-1]["levels"] if timeline else []
    # Within-league rate changes are observable, unlike unadjusted cross-league
    # comparisons. Do not infer causes or generalize from very small samples.
    by_league = defaultdict(list)
    for entry in timeline:
        for level in entry["levels"]:
            if level.get("points_per_game") is not None:
                by_league[level["league"]].append((entry["season"], level))
    production_changes = []
    for league, observations in by_league.items():
        for (previous_year, previous), (current_year, current) in zip(observations, observations[1:]):
            old, new = previous["points_per_game"], current["points_per_game"]
            if current_year <= previous_year or old is None or new is None:
                continue
            if not previous.get("games") or not current.get("games"):
                continue
            production_changes.append({"league":league,"from_season":previous_year,"to_season":current_year,
                "from_ppg":old,"to_ppg":new,"change_ppg":round(new-old,3),
                "from_games":previous["games"],"to_games":current["games"]})
    latest_games = latest_nhl.get("games") if latest_nhl else None
    return {"timeline": timeline, "transitions": transitions,"within_league_production_changes":production_changes,
            "first_observed_nhl_season": first_nhl,
            "first_observed_nhl_age_approx": first_nhl - birth_year if first_nhl and isinstance(birth_year, int) else None,
            "latest_nhl_regular_season": latest_nhl,
            "latest_levels": [x["league"] for x in last_levels],
            "nhl_sample_state": "immature" if latest_games is not None and latest_games < 20 else
                                "developing" if latest_games is not None and latest_games < 82 else
                                "larger_sample" if latest_games is not None else "unavailable",
            "limits": ["Observed level transitions do not establish promotion causes or NHL readiness at earlier dates.",
                       "League-to-league scoring rates are not directly comparable without normalization.",
                       "Season-start age is approximate and requires verified birth date for precise debut age."]}


def summarize_development(interpretation: Dict[str, Any]) -> List[str]:
    timeline = interpretation.get("timeline") or []
    if not timeline:
        return ["No season-level development record is available to interpret."]
    sentences = []
    for season in timeline[-6:]:
        fragments = []
        for level in season["levels"]:
            gp, pts = level["games"], level["points"]
            fragment = level["league"]
            if gp is not None:
                fragment += f" ({gp:g} GP"
                if pts is not None:
                    fragment += f", {pts:g} P"
                fragment += ")"
            fragments.append(fragment)
        sentences.append(f"{season['season']}-{str(season['season']+1)[-2:]}: " + ", ".join(fragments))
    results = ["Season chronology (most recent six observed seasons): " + "; ".join(sentences) + "."]
    changes = interpretation.get("transitions") or []
    if changes:
        recent = changes[-3:]
        results.append("Observed level transitions: " + "; ".join(
            f"{t['from_season']}→{t['to_season']}: {', '.join(t['from_levels'])} to {', '.join(t['to_levels'])}"
            for t in recent) + ". These document progression, not its causes.")
    changes=interpretation.get("within_league_production_changes") or []
    if changes:
        significant=[c for c in changes if abs(c["change_ppg"])>=0.15 and c["from_games"]>=10 and c["to_games"]>=10]
        if significant:
            strongest=sorted(significant,key=lambda c:abs(c["change_ppg"]),reverse=True)[0]
            direction="increased" if strongest["change_ppg"]>0 else "decreased"
            results.append(f"Within-league production: {strongest['league']} points per game {direction} from {strongest['from_ppg']:.3f} in {strongest['from_season']}-{str(strongest['from_season']+1)[-2:]} ({strongest['from_games']:g} GP) to {strongest['to_ppg']:.3f} in {strongest['to_season']}-{str(strongest['to_season']+1)[-2:]} ({strongest['to_games']:g} GP). This is an observed scoring-rate change, not proof of an improvement in underlying talent or a cause of promotion.")
    nhl = interpretation.get("latest_nhl_regular_season")
    if nhl:
        gp, pts = nhl["games"], nhl["points"]
        if gp is not None:
            results.append(f"Latest observed NHL regular-season sample: {gp:g} games" +
                           (f", {pts:g} points" if pts is not None else "") +
                           ". It provides attainment evidence; role stability and impact need additional deployment evidence.")
    return results
