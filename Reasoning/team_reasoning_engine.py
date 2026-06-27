"""Public Team Reasoning Engine for drop4e39.

This module turns seed public team profiles into deterministic team reasoning
objects. It deliberately stays in the Reasoning layer: public team profiles own
facts, this engine owns conclusions, and Scout/public answer helpers own
presentation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List


@dataclass(frozen=True)
class TeamReasoningSection:
    name: str
    conclusion: str
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "conclusion": self.conclusion, "evidence": list(self.evidence)}


@dataclass(frozen=True)
class TeamReasoningAssessment:
    team_id: str
    display_name: str
    executive_summary: str
    historical_context: TeamReasoningSection
    organizational_identity: TeamReasoningSection
    strengths: TeamReasoningSection
    weaknesses: TeamReasoningSection
    current_direction: TeamReasoningSection
    future_outlook: TeamReasoningSection
    confidence: float
    limitations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "display_name": self.display_name,
            "executive_summary": self.executive_summary,
            "historical_context": self.historical_context.to_dict(),
            "organizational_identity": self.organizational_identity.to_dict(),
            "strengths": self.strengths.to_dict(),
            "weaknesses": self.weaknesses.to_dict(),
            "current_direction": self.current_direction.to_dict(),
            "future_outlook": self.future_outlook.to_dict(),
            "confidence": self.confidence,
            "limitations": list(self.limitations),
        }


def _text(profile: Any, attr: str, default: str = "") -> str:
    return str(getattr(profile, attr, default) or default).strip()


def _questions(profile: Any) -> List[str]:
    values = getattr(profile, "public_questions", []) or []
    return [str(item).strip() for item in values if str(item).strip()]


def _limitations(profile: Any) -> List[str]:
    values = getattr(profile, "known_limitations", []) or []
    return [str(item).strip() for item in values if str(item).strip()]


def _has_any(haystack: Iterable[str], needles: Iterable[str]) -> bool:
    text = " ".join(haystack).lower()
    return any(needle in text for needle in needles)


class TeamReasoningEngine:
    """Build deterministic public team assessments from public team facts."""

    version = "drop4e39"

    def reason_about_public_team(self, profile: Any, question: str = "") -> TeamReasoningAssessment:
        display_name = _text(profile, "display_name", "Unknown team")
        identity = _text(profile, "identity", "Seed team identity is not available yet.")
        history = _text(profile, "history", "Historical profile is not available yet.")
        org_context = _text(profile, "organizational_context", "Organizational context is not available yet.")
        roster_context = _text(profile, "roster_context", "Roster context is not available yet.")
        league = _text(profile, "league", "NHL")
        conference = _text(profile, "conference", "")
        division = _text(profile, "division", "")
        tags = _questions(profile)
        limitations = _limitations(profile)

        evidence_base = [identity, history, org_context, roster_context, " ".join(tags), question]

        if history and history != "Historical profile is not available yet.":
            historical = history
        elif _has_any(evidence_base, ["original six", "market pressure", "playoff scrutiny"]):
            historical = f"{display_name} is an Original Six organization with a long NHL history and a high-pressure Toronto market context."
        elif _has_any(evidence_base, ["championship", "proven championship", "contender"]):
            historical = f"{display_name} has a contender-window history; current evaluation depends on whether elite talent is converting into championship-level outcomes."
        elif _has_any(evidence_base, ["possession", "process", "structure"]):
            historical = f"{display_name} has a modern process-driven identity built around structure and repeatable team play."
        else:
            historical = f"{display_name} has seed-level historical context only; deeper era, playoff and roster-cycle history is a future input."

        if _has_any(evidence_base, ["star", "elite", "franchise", "mcdavid", "draisaitl", "mackinnon", "makar", "matthews"]):
            strength = "High-end star identity gives the organization a clear top-of-roster foundation."
        elif _has_any(evidence_base, ["structure", "system", "two-way", "possession"]):
            strength = "System structure and two-way process are the strongest current organizational signals."
        else:
            strength = "The seed profile establishes a recognizable organizational identity, but not enough evidence for a full strengths model."

        if _has_any(evidence_base, ["goaltending", "defense", "depth", "health", "cap", "playoff scoring", "finishing", "roster balance"]):
            weakness = "The main unresolved risks are the supporting variables around the core: depth, health, balance, finishing, cap or goalie/defense context."
        elif limitations:
            weakness = "The main weakness in Athena's current read is evidence coverage: live roster, standings, injuries, transactions and cap context are not attached yet."
        else:
            weakness = "No major weakness can be concluded from the current seed profile alone."

        current_direction = org_context
        future_outlook = (
            f"Future outlook depends on current roster movement, health, depth, cap flexibility, transactions, and event context. "
            f"The current seed profile can describe {display_name} at a high level, but live roster/cap feeds are needed for a precise current assessment."
        )
        executive_summary = (
            f"{display_name} are {identity[0].lower() + identity[1:] if identity else 'a seed-level public team profile'}. "
            f"{historical} {org_context}"
        )

        sections = {
            "historical_context": TeamReasoningSection(
                "Historical Context",
                historical,
                [identity, history],
            ),
            "organizational_identity": TeamReasoningSection(
                "Organizational Identity",
                identity,
                [org_context],
            ),
            "strengths": TeamReasoningSection(
                "Strengths",
                strength,
                [roster_context, ", ".join(tags) if tags else "Public question tags are seed pending."],
            ),
            "weaknesses": TeamReasoningSection(
                "Weaknesses",
                weakness,
                limitations or ["Live evidence feeds are future inputs."],
            ),
            "current_direction": TeamReasoningSection(
                "Current Direction",
                current_direction,
                [org_context, roster_context],
            ),
            "future_outlook": TeamReasoningSection(
                "Future Outlook",
                future_outlook,
                ["Event Intelligence and expanded team knowledge packs are future inputs."],
            ),
        }

        confidence = 0.82 if identity and org_context and roster_context else 0.62
        if limitations:
            confidence = min(confidence, 0.80)

        return TeamReasoningAssessment(
            team_id=_text(profile, "entity_id", "unknown"),
            display_name=display_name,
            executive_summary=executive_summary,
            historical_context=sections["historical_context"],
            organizational_identity=sections["organizational_identity"],
            strengths=sections["strengths"],
            weaknesses=sections["weaknesses"],
            current_direction=sections["current_direction"],
            future_outlook=sections["future_outlook"],
            confidence=confidence,
            limitations=limitations + [
                "drop4e39 uses public team seed profiles; live standings, injuries, cap, transactions and roster feeds are not attached yet."
            ],
        )
