"""Comparison Intelligence Engine for drop4e40.

This module converts public player/team seed profiles into structured comparative
reasoning. Knowledge owns the profile facts; this engine owns conclusions;
Scout/public answer helpers own presentation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Sequence


@dataclass(frozen=True)
class ComparisonSection:
    name: str
    conclusion: str
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "conclusion": self.conclusion, "evidence": list(self.evidence)}


@dataclass(frozen=True)
class ComparisonAssessment:
    comparison_type: str
    subject_a: str
    subject_b: str
    executive_comparison: str
    strengths: ComparisonSection
    weaknesses: ComparisonSection
    historical_comparison: ComparisonSection
    prime_comparison: ComparisonSection
    future_outlook: ComparisonSection
    athena_conclusion: str
    confidence: float
    evidence_summary: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "comparison_type": self.comparison_type,
            "subject_a": self.subject_a,
            "subject_b": self.subject_b,
            "executive_comparison": self.executive_comparison,
            "strengths": self.strengths.to_dict(),
            "weaknesses": self.weaknesses.to_dict(),
            "historical_comparison": self.historical_comparison.to_dict(),
            "prime_comparison": self.prime_comparison.to_dict(),
            "future_outlook": self.future_outlook.to_dict(),
            "athena_conclusion": self.athena_conclusion,
            "confidence": self.confidence,
            "evidence_summary": list(self.evidence_summary),
            "limitations": list(self.limitations),
        }


def _text(obj: Any, attr: str, default: str = "") -> str:
    return str(getattr(obj, attr, default) or default).strip()


def _list(obj: Any, attr: str) -> List[str]:
    values = getattr(obj, attr, []) or []
    return [str(item).strip() for item in values if str(item).strip()]


def _tag_text(tags: Iterable[str]) -> str:
    pretty = [str(tag).replace("_", " ") for tag in tags if str(tag).strip()]
    return ", ".join(pretty) if pretty else "seed pending"


def _contains(tags: Iterable[str], *needles: str) -> bool:
    text = " ".join(tags).lower()
    return any(needle in text for needle in needles)


def _player_strength(name: str, tags: Sequence[str], value: str, style: str) -> str:
    if _contains(tags, "generational", "transition", "playmaking", "speed"):
        return f"{name} has the stronger creation/transition profile, with value driven by pace, puck transport and playmaking pressure."
    if _contains(tags, "goal_scoring", "elite_finisher", "shooting"):
        return f"{name} has the cleaner goal-scoring edge, with value concentrated in shot generation and finishing."
    if _contains(tags, "complete_center", "championship", "leadership"):
        return f"{name} has the broader legacy/complete-center case, especially where leadership, detail play and championship context matter."
    if _contains(tags, "defenseman", "transition_driver", "power_play"):
        return f"{name} stands out through modern defense/transition value and power-play orchestration."
    if value:
        return f"{name} is best framed as {value.lower()}, with style evidence around {style}."
    return f"{name} has a recognizable public profile, but the current seed pack does not yet isolate a single dominant edge."


def _player_weakness(name: str, profile: Any) -> str:
    limits = _list(profile, "known_limitations")
    if limits:
        return f"The main limitation for {name} is evidence coverage: live injuries, current deployment, official current-season stats and age-curve feeds are not attached yet."
    return f"No hard weakness is concluded for {name} from the public seed profile alone."


def _team_strength(name: str, questions: Sequence[str], identity: str, roster_context: str) -> str:
    if _contains(questions, "star core", "elite", "championship window", "center depth"):
        return f"{name}'s comparative strength is top-end talent and a clear contention window."
    if _contains(questions, "system strength", "team structure", "possession", "process"):
        return f"{name}'s comparative strength is repeatable structure and possession/process identity."
    if _contains(questions, "market pressure", "playoff ceiling"):
        return f"{name}'s advantage is brand/star visibility, but that also raises the playoff-translation bar."
    return f"{name}'s seed profile emphasizes {identity or roster_context or 'organizational identity'}."


def _team_weakness(name: str, questions: Sequence[str], limitations: Sequence[str]) -> str:
    if _contains(questions, "goaltending", "defense", "depth", "health", "cap", "roster balance", "playoff scoring"):
        return f"{name}'s comparative risk is the support layer around its identity: depth, balance, health, cap, defense/goaltending or playoff finishing."
    if limitations:
        return f"{name}'s biggest current limitation in Athena is missing live team evidence: roster, standings, injury, cap and transaction feeds."
    return f"No major organizational weakness can be concluded for {name} from seed context alone."


class ComparisonReasoningEngine:
    """Build deterministic public comparison assessments."""

    version = "drop4e40"

    def compare_public_players(self, profile_a: Any, profile_b: Any, question: str = "") -> ComparisonAssessment:
        a = _text(profile_a, "display_name", "Player A")
        b = _text(profile_b, "display_name", "Player B")
        tags_a = _list(profile_a, "comparison_tags")
        tags_b = _list(profile_b, "comparison_tags")
        shared = sorted(set(tags_a).intersection(tags_b))
        a_only = sorted(set(tags_a) - set(tags_b))
        b_only = sorted(set(tags_b) - set(tags_a))
        style_a = _text(profile_a, "style", "style seed pending")
        style_b = _text(profile_b, "style", "style seed pending")
        value_a = _text(profile_a, "public_value", "")
        value_b = _text(profile_b, "public_value", "")

        executive = (
            f"{a} vs {b} is no longer just a profile juxtaposition: Athena compares role, style, peak identity, career context and future uncertainty. "
            f"{a} is framed around {value_a.lower() or 'public player value'}, while {b} is framed around {value_b.lower() or 'public player value'}."
        )
        strengths = ComparisonSection(
            "Relative Strengths",
            f"{_player_strength(a, tags_a, value_a, style_a)} {_player_strength(b, tags_b, value_b, style_b)}",
            [f"{a} tags: {_tag_text(a_only or tags_a)}.", f"{b} tags: {_tag_text(b_only or tags_b)}."],
        )
        weaknesses = ComparisonSection(
            "Relative Weaknesses",
            f"{_player_weakness(a, profile_a)} {_player_weakness(b, profile_b)}",
            _list(profile_a, "known_limitations") + _list(profile_b, "known_limitations"),
        )
        historical = ComparisonSection(
            "Historical Comparison",
            f"Historically, {a} is seeded as {(_text(profile_a, 'career_identity') or value_a).rstrip('.')}. {b} is seeded as {(_text(profile_b, 'career_identity') or value_b).rstrip('.')}. Shared context: {_tag_text(shared)}.",
            _list(profile_a, "career_notes")[:3] + _list(profile_b, "career_notes")[:3],
        )
        prime = ComparisonSection(
            "Prime Comparison",
            self._prime_player_read(a, b, tags_a, tags_b),
            [f"{a} style: {style_a}.", f"{b} style: {style_b}."],
        )
        future = ComparisonSection(
            "Future Outlook",
            f"Future outlook depends on live age-curve, health, deployment, teammate and current-season evidence. In this build, Athena can compare public identity and seeded career context, but not real-time trajectory.",
            ["Current official statistics, live injury status and deployment feeds are future inputs."],
        )
        conclusion = self._player_conclusion(a, b, tags_a, tags_b, value_a, value_b)
        confidence = 0.84 if (tags_a and tags_b and _text(profile_a, "career_identity") and _text(profile_b, "career_identity")) else 0.68
        limitations = sorted(set(_list(profile_a, "known_limitations") + _list(profile_b, "known_limitations") + [
            "drop4e40 compares public seed profiles; full official statistics, playoff splits, age curves and live event inputs arrive later."
        ]))
        return ComparisonAssessment(
            comparison_type="public_player_comparison",
            subject_a=a,
            subject_b=b,
            executive_comparison=executive,
            strengths=strengths,
            weaknesses=weaknesses,
            historical_comparison=historical,
            prime_comparison=prime,
            future_outlook=future,
            athena_conclusion=conclusion,
            confidence=confidence,
            evidence_summary=[
                "public player profile seed",
                "public identity graph",
                "career identity notes",
                "style and comparison tags",
            ],
            limitations=limitations,
        )

    def compare_public_teams(self, profile_a: Any, profile_b: Any, question: str = "") -> ComparisonAssessment:
        a = _text(profile_a, "display_name", "Team A")
        b = _text(profile_b, "display_name", "Team B")
        q_a = _list(profile_a, "public_questions")
        q_b = _list(profile_b, "public_questions")
        identity_a = _text(profile_a, "identity", "")
        identity_b = _text(profile_b, "identity", "")
        roster_a = _text(profile_a, "roster_context", "")
        roster_b = _text(profile_b, "roster_context", "")
        shared = sorted(set(q_a).intersection(q_b))

        executive = (
            f"{a} vs {b} is an organizational comparison. Athena compares identity, competitive window, star/core profile, structure, risk and future context rather than listing two team blurbs."
        )
        strengths = ComparisonSection(
            "Relative Strengths",
            f"{_team_strength(a, q_a, identity_a, roster_a)} {_team_strength(b, q_b, identity_b, roster_b)}",
            [f"{a}: {identity_a}", f"{b}: {identity_b}"],
        )
        weaknesses = ComparisonSection(
            "Relative Weaknesses",
            f"{_team_weakness(a, q_a, _list(profile_a, 'known_limitations'))} {_team_weakness(b, q_b, _list(profile_b, 'known_limitations'))}",
            _list(profile_a, "known_limitations") + _list(profile_b, "known_limitations"),
        )
        historical = ComparisonSection(
            "Historical Comparison",
            f"The current seed pack compares organizational archetype, not full franchise history. {a} is framed as {identity_a.lower()}. {b} is framed as {identity_b.lower()}.",
            [f"Shared team questions: {_tag_text(shared)}."],
        )
        prime = ComparisonSection(
            "Prime Comparison",
            f"Prime/team-peak comparison is provisional until deeper historical team packs arrive. The current read compares present organizational peak signals: {a}'s {roster_a.lower()} against {b}'s {roster_b.lower()}.",
            [roster_a, roster_b],
        )
        future = ComparisonSection(
            "Future Outlook",
            f"Future outlook turns on live roster movement, cap flexibility, injuries, standings, prospect pipeline and event intelligence. Those feeds are intentionally outside drop4e40.",
            ["Event Intelligence, roster feeds, cap feeds and prospect packs are future inputs."],
        )
        conclusion = (
            f"Athena's current conclusion: choose {a} when the question prioritizes {q_a[0] if q_a else 'its seeded organizational identity'}; choose {b} when the question prioritizes {q_b[0] if q_b else 'its seeded organizational identity'}. "
            "A stronger final verdict requires live team evidence."
        )
        limitations = sorted(set(_list(profile_a, "known_limitations") + _list(profile_b, "known_limitations") + [
            "drop4e40 compares seeded public team profiles; live standings, injuries, transactions, cap and prospect pipeline feeds arrive later."
        ]))
        return ComparisonAssessment(
            comparison_type="public_team_comparison",
            subject_a=a,
            subject_b=b,
            executive_comparison=executive,
            strengths=strengths,
            weaknesses=weaknesses,
            historical_comparison=historical,
            prime_comparison=prime,
            future_outlook=future,
            athena_conclusion=conclusion,
            confidence=0.80 if identity_a and identity_b else 0.62,
            evidence_summary=["public team profile seed", "public identity graph", "organizational context", "team question tags"],
            limitations=limitations,
        )

    def _prime_player_read(self, a: str, b: str, tags_a: Sequence[str], tags_b: Sequence[str]) -> str:
        if _contains(tags_a, "goal_scoring") and _contains(tags_b, "playmaking", "transition", "generational"):
            return f"At their respective peaks, {a} owns the more specialized goal-scoring argument, while {b} owns the broader offensive-creation argument."
        if _contains(tags_b, "goal_scoring") and _contains(tags_a, "playmaking", "transition", "generational"):
            return f"At their respective peaks, {b} owns the more specialized goal-scoring argument, while {a} owns the broader offensive-creation argument."
        if _contains(tags_a, "legacy", "championship") or _contains(tags_b, "legacy", "championship"):
            return f"Prime comparison requires separating single-season ceiling from legacy weight; championship and leadership evidence matter more for the legacy side than for pure peak skill."
        return f"Prime comparison is currently based on seeded role/style evidence; deeper statistical peak modelling is a future comparison pack."

    def _player_conclusion(self, a: str, b: str, tags_a: Sequence[str], tags_b: Sequence[str], value_a: str, value_b: str) -> str:
        if _contains(tags_a, "goal_scoring") and _contains(tags_b, "playmaking", "transition", "generational"):
            return f"Overall, {a} is the cleaner pure-finishing choice, while {b} is the broader creation/transition choice. The better answer depends on whether the user values goal scoring or total offensive control."
        if _contains(tags_b, "goal_scoring") and _contains(tags_a, "playmaking", "transition", "generational"):
            return f"Overall, {b} is the cleaner pure-finishing choice, while {a} is the broader creation/transition choice. The better answer depends on whether the user values goal scoring or total offensive control."
        if _contains(tags_a, "complete_center", "legacy") or _contains(tags_b, "complete_center", "legacy"):
            return f"Overall, this comparison should be read through context: current peak value, all-time legacy, complete-game impact and championship evidence may point to different answers."
        return f"Overall, {a} and {b} compare as {value_a.lower() or 'public assets'} versus {value_b.lower() or 'public assets'}; Athena needs richer statistical and event evidence for a stronger final ranking."
