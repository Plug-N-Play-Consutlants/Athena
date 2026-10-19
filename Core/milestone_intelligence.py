"""Evidence-first milestone checks for real Scout acceptance.

A milestone is a human-reviewed real-world execution, never a fixture PASS.
This module defines repeatable prompts and grades only documented observations.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Mapping

MILESTONES = {
    "0.7.10.34.0": (
        ("public", "What is Toronto's current itemized NHL cap position, including missing obligations and as-of dates?"),
        ("public", "Could Toronto acquire a $7M player in a trade without losing a core roster piece? Address cap, roster fit, and trade feasibility."),
        ("public", "Which available free agents could help Toronto's defense, and can the team afford to sign one?"),
        ("public", "Can Toronto sign another player under the 50-SPC limit, reserve-list rules and roster limits?"),
        ("public", "What does an injured player's LTIR designation actually permit Toronto to do today?"),
        ("public", "Can Toronto recall a two-way contract player today? Explain waiver, salary, roster and cap differences."),
        ("public", "Should Toronto extend a pending free agent now or preserve cap flexibility for next summer?"),
        ("public", "Could Toronto trade a contract, recall a prospect and then sign a free agent? Explain transaction order and unknowns."),
        ("public", "Toronto needs a reliable defenseman before the deadline. What are realistic options?"),
    ),
    "0.7.10.36.0": (
        ("public", "How could Toronto improve its forward group without trading Matthew Knies, given its cap and organizational depth?"),
        ("public", "Compare a short-term scoring upgrade against preserving cap flexibility next season."),
    ),
    "0.7.10.38.0": (
        ("public", "Reconstruct the Marchenko–Knies trade from information known at the time; distinguish observers' concerns from the GM's unconfirmed intentions."),
        ("public", "Assess the Maple Leafs' scoring, goaltending, contracts and roster options together, identifying unresolved evidence."),
        ("public", "Which JHLPAA managers have been most active recently and what changed?"),
    ),
    "0.7.10.39.0": (
        ("public", "Explain Toronto's cap position, its biggest roster weakness and two CBA-compliant options to improve it."),
        ("public", "I refuse to trade Knies. Re-evaluate the best alternatives and their opportunity costs."),
        ("fantasy", "What changed across the JHLPAA this week, and who deserves recognition?"),
    ),
}
REQUIRED_FIELDS = ("real_scout_execution", "source_provenance", "routing", "reasoning", "communication", "boundaries")
DECISION_DIMENSIONS = ("hockey_intelligence", "cap_cba_intelligence", "decision_intelligence")

@dataclass(frozen=True)
class MilestoneAssessment:
    milestone: str
    status: str
    findings: tuple[str, ...]
    def to_dict(self):
        return asdict(self)

def assess_milestone(milestone: str, observations: Mapping[str, Mapping[str, str]]) -> MilestoneAssessment:
    """Grade externally observed Scout runs. Never infer PASS from a synthetic test."""
    if milestone not in MILESTONES:
        raise ValueError("Unknown milestone")
    findings=[]
    outcomes=[]
    for index, (_, prompt) in enumerate(MILESTONES[milestone], 1):
        observation=observations.get(str(index), {})
        missing=[field for field in REQUIRED_FIELDS if field not in observation]
        if missing:
            findings.append(f"Prompt {index}: unreviewed ({', '.join(missing)})")
            outcomes.append("PARTIAL")
            continue
        values=[str(observation[field]).upper() for field in REQUIRED_FIELDS]
        if any(value not in ("PASS", "PARTIAL", "FAIL", "BLOCKED") for value in values):
            raise ValueError(f"Prompt {index}: invalid assessment")
        status=("FAIL" if "FAIL" in values else "BLOCKED" if "BLOCKED" in values else
                "PARTIAL" if "PARTIAL" in values else "PASS")
        outcomes.append(status)
        findings.append(f"Prompt {index}: {status} — {prompt}")
    status=("FAIL" if "FAIL" in outcomes else "BLOCKED" if "BLOCKED" in outcomes else
            "PARTIAL" if "PARTIAL" in outcomes else "PASS")
    return MilestoneAssessment(milestone, status, tuple(findings))

def milestone_checklist(milestone: str) -> str:
    if milestone not in MILESTONES:
        raise ValueError("Unknown milestone")
    lines=[f"Milestone Intelligence Check — {milestone}",
           "Run these in the NORMAL Scout interface. Record real evidence and full replies.",
           "Studio does not certify live access, factual accuracy, or a PASS by listing prompts."]
    for i,(mode,prompt) in enumerate(MILESTONES[milestone],1):
        lines.append(f"{i}. [{mode.upper()}] {prompt}")
    lines.append("Review: real Scout execution, source provenance, routing, reasoning, communication, boundaries.")
    lines.append("For each scenario also record hockey, cap/CBA and decision intelligence separately; distinguish NOT YET IMPLEMENTED from missing evidence.")
    lines.append("An answer that gets the math right but misses the hockey question is not a full PASS.")
    lines.append("Outcomes: PASS / PARTIAL / FAIL / BLOCKED. Missing observations cannot PASS.")
    return "\n".join(lines)
