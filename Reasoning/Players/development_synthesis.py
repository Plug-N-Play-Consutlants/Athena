"""Evidence-bounded development synthesis shared across player and organization inquiries."""
from __future__ import annotations
from typing import Any, Dict

def synthesize_development(interpretation: Dict[str, Any]) -> Dict[str, Any]:
    changes = interpretation.get("within_league_production_changes") or []
    qualified = [x for x in changes if (x.get("from_games") or 0) >= 15 and (x.get("to_games") or 0) >= 15
                 and isinstance(x.get("change_ppg"), (float, int))]
    findings = []
    for x in sorted(qualified, key=lambda x: abs(x["change_ppg"]), reverse=True)[:2]:
        delta = x["change_ppg"]
        if abs(delta) < .15: continue
        direction = "increased" if delta > 0 else "decreased"
        findings.append(f"At the {x['league']} level, observed scoring rate {direction} by "
            f"{abs(delta):.3f} points/game ({x['from_ppg']:.3f} to {x['to_ppg']:.3f}) "
            f"across {x['from_games']:g} and {x['to_games']:g} games. "
            "This is a directional performance signal, not an adjusted talent estimate.")
    nhl = interpretation.get("latest_nhl_regular_season") or {}
    nhl_games = nhl.get("games")
    if isinstance(nhl_games, (int, float)) and nhl_games > 0:
        findings.append(f"An observed {nhl_games:g}-game NHL sample establishes NHL attainment, "
                        "but not a stable role or NHL impact.")
    if not findings:
        findings.append("Season observations do not establish a robust within-league scoring trend or stable NHL role.")
    return {"state": "supported_inference" if qualified else "bounded_inference",
            "findings": findings,
            "decision_implication": "Development evidence can inform organizational optionality, but without verified role, opportunity and full-population attainment baselines it cannot establish a trade-value premium or precise NHL ceiling.",
            "limits": ["Production does not measure defensive or off-puck impact.",
                       "NHL attainment is not equivalent to NHL role security.",
                       "Missing cohorts limit relative outcomes, not within-player observed changes."]}
