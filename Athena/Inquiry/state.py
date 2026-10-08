"""Normalize user inquiry semantics before domain specialists execute.

This layer intentionally knows about inquiry semantics, not answers. Professional
and fantasy paths consume the same state while retaining domain-specific evidence.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

@dataclass(frozen=True)
class TemporalScope:
    kind: str = "current"
    value: Optional[int] = None
    label: str = "current"
    source: str = "default"

@dataclass
class InquiryState:
    raw_question: str
    mode: str
    subjects: List[str] = field(default_factory=list)
    organizations: List[str] = field(default_factory=list)
    operation: str = "analyze"
    temporal_scope: TemporalScope = field(default_factory=TemporalScope)
    protected_assets: List[str] = field(default_factory=list)
    named_outgoing_assets: List[str] = field(default_factory=list)
    constraints_enforced: List[str] = field(default_factory=list)
    constraints_waived: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    scenario_mode: str = "real_world"
    plausibility_requested: bool = False
    evidence_requirements: List[str] = field(default_factory=list)
    unresolved_inputs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data


def _temporal_scope(q: str) -> TemporalScope:
    if re.search(r"\b(last|past|previous)\s+week\b", q):
        return TemporalScope("relative_period", 1, "last week", "user")
    m = re.search(r"\b(?:last|past|previous|over the last|over the past)\s+(\d+)\s+seasons?\b", q)
    if m:
        n = int(m.group(1)); return TemporalScope("season_window", n, f"last {n} seasons", "user")
    words = {"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,"ten":10}
    m = re.search(r"\b(?:last|past|previous|over the last|over the past)\s+(two|three|four|five|six|seven|eight|nine|ten)\s+seasons?\b", q)
    if m:
        n=words[m.group(1)]; return TemporalScope("season_window", n, f"last {n} seasons", "user")
    if re.search(r"\b(whole|entire|full)\s+career\b|\bcareer\s+(history|stats|statistics)\b", q):
        return TemporalScope("career", None, "career", "user")
    m = re.search(r"\b(first)\s+(\d+)\s+seasons?\b", q)
    if m:
        n=int(m.group(2)); return TemporalScope("career_opening_window", n, f"first {n} seasons", "user")
    return TemporalScope()


def build_inquiry_state(question: str, mode: str = "public") -> InquiryState:
    raw=(question or "").strip(); q=raw.casefold()
    state=InquiryState(raw_question=raw, mode=(mode or "public").strip().lower(), temporal_scope=_temporal_scope(q))
    # Resolve player subjects through Athena's identity layer where possible.
    try:
        from Athena.intent_planner import _public_player_subjects_for
        state.subjects=[str(s.get("name")) for s in _public_player_subjects_for(raw) if s.get("name")]
    except Exception:
        state.subjects=[]
    if any(x in q for x in ("toronto", "maple leafs", "leafs")): state.organizations.append("Toronto Maple Leafs")
    if any(x in q for x in ("edmonton", "oilers")): state.organizations.append("Edmonton Oilers")
    if any(x in q for x in ("trade", "acquire", "acquisition", "get ", "deal for")): state.operation="transaction"
    elif any(x in q for x in ("compare", " versus ", " vs ")): state.operation="compare"
    elif any(x in q for x in ("summarize", "summarise", "recap", "what happened")): state.operation="summarize"
    if any(x in q for x in ("what if", "hypothetical", "could ", "how could", "imagine", "assume", "pretend")):
        state.scenario_mode="hypothetical"
    if any(x in q for x in ("realistic", "realistically", "plausible", "plausibility", "make sense", "why would", "fit for")):
        state.plausibility_requested=True
    # Preserve an explicit named outgoing package as scenario authority. This is
    # intentionally syntactic: player identity enrichment can happen downstream,
    # but the user's named package must survive even when a prospect is not in the
    # planner's compact identity registry.
    if state.operation == "transaction":
        m=re.search(r"\b(?:acquire|get|trade for)\s+[A-Z][A-Za-z .'-]+?\s+for\s+(.+?)(?=\s+without\s+|\s*,?\s*should\s+|\s*\?\s*|$)", raw, re.I)
        if m:
            package_text=m.group(1).strip().rstrip(" ,.")
            parts=re.split(r"\s*,\s*|\s+and\s+", package_text, flags=re.I)
            state.named_outgoing_assets=[x.strip() for x in parts if x.strip()]
    # Negative/protected asset constraints survive routing as structured state.
    protected_patterns=[r"without (?:trading|giving up|moving|including)\s+([a-z][a-z .'-]+?)(?:\?|,|\.|$|\s+and\s+)",
                        r"do not (?:trade|move|include)\s+([a-z][a-z .'-]+?)(?:\?|,|\.|$)"]
    for pattern in protected_patterns:
        for value in re.findall(pattern,q):
            name=value.strip().title()
            if name and name not in state.protected_assets: state.protected_assets.append(name)
    # A transaction may protect a resolved entity directly ("without Matthews")
    # without repeating a transaction verb. Resolve only against known subjects
    # so generic "without X" prose does not become an arbitrary asset.
    if state.operation == "transaction":
        for subject in state.subjects:
            sf=subject.casefold().strip()
            aliases={sf, sf.split()[-1]}
            if any(re.search(r"\bwithout\s+" + re.escape(alias) + r"\b", q) for alias in aliases if alias):
                if subject not in state.protected_assets:
                    state.protected_assets.append(subject)
    # Reconcile protected mentions to canonical resolved subject identities.
    # Routing and downstream specialists should not have to decide whether
    # "Matthews" and "Auston Matthews" represent the same protected asset.
    canonical_protected=[]
    for protected in state.protected_assets:
        p=protected.casefold().strip()
        match=None
        for subject in state.subjects:
            sf=subject.casefold().strip()
            if p == sf or p == sf.split()[-1] or sf.endswith(" " + p):
                match=subject; break
        canonical_protected.append(match or protected)
    state.protected_assets=list(dict.fromkeys(canonical_protected))
    if not state.organizations and state.operation == "transaction":
        protected_text=" ".join(state.protected_assets).casefold()
        if "matthews" in protected_text:
            state.organizations.append("Toronto Maple Leafs")
    cap_waiver = (
        re.search(r"\b(forget|ignore|disregard|without considering)\b.{0,35}\b(salary cap|cap)\b", q)
        or re.search(r"\b(pretend|assume|imagine)\b.{0,45}\b(salary cap|cap)\b.{0,30}\b(not|isn't|is not|wasn't|was not)\b.{0,20}\b(issue|factor|constraint|problem|consideration)\b", q)
        or re.search(r"\b(salary cap|cap)\b.{0,25}\b(not|isn't|is not|doesn't|does not)\b.{0,20}\b(matter|apply|issue|factor|constraint|problem)\b", q)
    )
    if cap_waiver:
        state.constraints_waived.append("salary_cap")
    if "salary_cap" not in state.constraints_waived and "salary cap" in q:
        state.constraints_enforced.append("salary_cap")
    # Evidence requirements describe what an investigation should seek; they do not claim availability.
    if state.operation == "transaction":
        state.evidence_requirements += ["resolved_player_identity", "organizational_state", "transaction_components"]
        if "salary_cap" not in state.constraints_waived: state.evidence_requirements += ["contract_state", "cap_cba_state"]
    if state.temporal_scope.kind != "current": state.evidence_requirements.append("time_scoped_evidence")
    if state.mode == "fantasy" and state.operation == "summarize":
        state.evidence_requirements += ["league_state", "time_scoped_transactions", "standings"]
    state.evidence_requirements=list(dict.fromkeys(state.evidence_requirements))
    return state


def select_primary_player_subject(question: str, profiles: List[Any]) -> Any | None:
    """Select the transaction subject while preserving protected/supporting entities."""
    if not profiles: return None
    inquiry=build_inquiry_state(question, "public")
    protected={x.casefold() for x in inquiry.protected_assets}
    for profile in profiles:
        name=str(getattr(profile,"display_name","") or "")
        if name.casefold() not in protected and not any(p in name.casefold() for p in protected if p):
            return profile
    return profiles[0] if len(profiles)==1 else None
