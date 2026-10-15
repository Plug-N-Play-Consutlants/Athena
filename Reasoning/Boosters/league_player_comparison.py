"""League-specific decision pass over a shared NHL player comparison.

No provider fetching or independent player evaluation belongs here. Only verified
league configuration and already-attributed official NHL comparison evidence may
be used. Unrecognized scoring models must not inherit JHLPAA assumptions.
"""
from __future__ import annotations


def _profile_data(profile):
    if isinstance(profile, dict):
        return profile
    return getattr(profile, "__dict__", {})


def _text(profile):
    data = _profile_data(profile)
    return str(data.get("display_name") or data.get("name") or "Unknown player")


def apply_league_player_comparison(answer, league_profile, profiles, recent_series):
    """Compose a bounded league decision from the existing shared comparison."""
    if not isinstance(league_profile, dict) or len(profiles) < 2:
        return answer
    league = str(league_profile.get("league_name") or "the selected league")
    scoring = str(league_profile.get("scoring_detail") or "").lower()
    model = str(league_profile.get("competition_model") or "").lower()
    names = [_text(p) for p in profiles[:2]]
    evidence = []
    rates = {}
    for name in names:
        rows = recent_series.get(name) or []
        gp = sum(int(r.get("gp") or 0) for r in rows if isinstance(r, dict))
        pts = sum(int(r.get("points") or 0) for r in rows if isinstance(r, dict))
        if gp > 0:
            rates[name] = pts / gp
            evidence.append(f"Verified NHL scoring window — {name}: {pts} G+A points in {gp} games ({pts/gp:.2f}/game).")
    parts = [f"{league} application (configured scoring: {scoring or 'unverified'}; competition: {model or 'unverified'})."]
    if scoring == "points_only" and model == "total_points":
        parts.append("This league rewards goals plus assists; shot volume, hits, blocks and other NHL statistics do not directly score under the verified league model.")
        if len(rates) == 2:
            ranked = sorted(rates.items(), key=lambda item: item[1], reverse=True)
            if abs(ranked[0][1] - ranked[1][1]) >= 0.01:
                parts.append(f"Based on the verified recent NHL G+A scoring rate, {ranked[0][0]} has the stronger historical production case ({ranked[0][1]:.2f} vs {ranked[1][1]:.2f} points/game). This is a production comparison, not a full keeper or trade valuation.")
            else:
                parts.append("The verified recent NHL G+A rates are effectively even.")
        else:
            parts.append("A verified comparable NHL G+A scoring window is unavailable in this request. No production winner is asserted.")
    else:
        parts.append("This scoring format requires a distinct verified scoring calculation. NHL point totals alone cannot determine the league-specific winner.")
    slots = league_profile.get("lineup_slots") or []
    centers = next((s.get("active_slots") for s in slots if isinstance(s, dict) and s.get("position") == "C"), None)
    if centers is not None:
        parts.append(f"Roster constraint: {centers} active C slots. Both compared players are centers; roster alternatives and eligibility must be evaluated before recommending a move.")
    keepers = league_profile.get("keeper_count")
    if keepers is not None:
        parts.append(f"Keeper context: {keepers} keeper slots. Contract terms, ownership, opportunity cost and keeper eligibility have not been verified for these two assets in this comparison.")
    parts.append("Current health, deployment and league-specific asset restrictions remain unresolved where not supplied as evidence.")
    narrative = "\n\n".join(parts)
    original = answer.get("natural_language_response") or answer.get("engine_conclusion") or ""
    answer["natural_language_response"] = str(original) + "\n\n" + narrative
    answer["engine_conclusion"] = narrative
    answer["intent"] = "league_player_comparison"
    answer["title"] = f"{names[0]} vs {names[1]} — {league}"
    answer.setdefault("observed_facts", []).extend(evidence)
    answer.setdefault("known_limitations", []).append("League asset ownership, contract eligibility, and current lineup evidence are not established by a public NHL comparison.")
    dev = answer.setdefault("developer", {})
    dev["intent"] = "league_player_comparison"
    dev.setdefault("intelligence_used", []).append("league_player_comparison_booster")
    dev["league_application"] = {"league": league, "scoring_detail": scoring, "competition_model": model, "verified_rates": rates}
    return answer
