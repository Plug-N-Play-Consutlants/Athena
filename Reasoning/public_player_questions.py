"""Question-scoped reasoning over a verified public player profile.

Identity is supplied by Athena. This module never resolves names or reads
fantasy player rows; it distinguishes established profile facts from questions
that need current, independent evidence.
"""
from __future__ import annotations

from typing import Any, Dict


def classify_player_question(question: str) -> str:
    text = str(question or "").casefold()
    if any(term in text for term in ("camp", "preseason", "pre-season", "early-season", "recent form", "latest evidence", "injury")):
        return "current_evidence"
    if any(term in text for term in ("uncertaint", "risk", "unknown", "biggest question", "what remains", "evidence-backed")):
        return "uncertainty"
    if any(term in text for term in ("develop", "transition", "trajectory", "career trend")):
        return "development"
    if any(term in text for term in ("fit", "roster", "organization", "role", "deployment")):
        return "organizational_fit"
    if any(term in text for term in ("outlook", "future", "project")):
        return "outlook"
    return "profile"


def assess_player_question(profile: Any, question: str) -> Dict[str, Any]:
    kind = classify_player_question(question)
    name = profile.display_name
    role = str(profile.role or f"{profile.position} in the public profile").strip().rstrip(".")
    established = f"The verified public profile identifies {name} as a {role}."
    facts = [established]
    if profile.draft:
        facts.append(f"Draft context: {profile.draft}.")
    limitations = []
    for item in profile.known_limitations:
        limit = str(item).strip().rstrip(".")
        if not limit:
            continue
        if "organization/status" in limit.casefold():
            limit = "Current organization and playing status have not been verified with a current source"
        elif "pif build" in limit.casefold():
            limit = "Current player evidence is incomplete: " + limit.split("does not yet", 1)[-1].strip() if "does not yet" in limit else "Current player evidence is incomplete"
        else:
            limit = limit.replace("before public release", "for a current assessment")
        limitations.append(limit)
    # The seed is a historical identity substrate, not a live roster source.
    if kind == "uncertainty":
        uncertainties = limitations or ["Current role, health, deployment, and comparable recent performance are not established by this profile"]
        conclusion = (
            f"The public profile describes {name} as a {role}. Its clearest unresolved point is: {uncertainties[0]}. "
            "That profile alone cannot establish a present role or a future outcome. "
            "A stronger outlook needs current organization and usage evidence, health context, and comparable recent performance."
        )
    elif kind == "current_evidence":
        conclusion = (f"I can identify {name}, but the player profile does not establish what happened in camp "
                      "or preseason. A current assessment needs dated reports tied to this player's identity "
                      "and deployment; without them, I cannot say whether the early-season outlook changed.")
    elif kind == "development":
        conclusion = (
            f"{name}'s draft and public role establish the starting point for a development assessment. "
            "The available profile does not establish a measured progression into a current NHL role. "
            "That inference needs dated deployment and performance evidence across seasons."
        )
    elif kind == "organizational_fit":
        conclusion = (
            f"The profile describes {name} as a {role}, associated with {profile.team}. "
            "Fit with a current roster cannot be established from that identity alone. "
            "Athena needs a verified current organization, roster needs, deployment, and alternatives before drawing a fit conclusion."
        )
    elif kind == "outlook":
        conclusion = (
            f"The supported starting point for {name}'s outlook is the {role} profile. "
            "A current projection needs verified team status, recent usage, health, and performance trends; those cannot be inferred from the seeded identity."
        )
    else:
        conclusion = established
    return {
        "kind": kind,
        "conclusion": conclusion,
        "facts": facts,
        "limitations": limitations or ["Current deployment and recent performance evidence are not attached to this public profile."],
        "confidence": 0.57 if kind != "profile" else 0.65,
    }
