"""Rule-based intent classifier for PIF-1 Build 001.

The first PIF layer is intentionally deterministic. Athena should know which
intelligence path a public question belongs to before it retrieves rulebooks,
player evidence, fantasy data, or event feeds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Dict, List

from .intent_types import IntentType


@dataclass(frozen=True)
class IntentResult:
    intent: IntentType
    confidence: float
    matched_terms: List[str] = field(default_factory=list)
    rationale: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "intent": self.intent.value,
            "confidence": self.confidence,
            "matched_terms": list(self.matched_terms),
            "rationale": self.rationale,
        }


_COMPARE_RE = re.compile(r"\b(compare|versus|vs\.?|better than|who is better|which is better)\b", re.I)
_PLAYER_COMMAND_RE = re.compile(r"^\s*(analy[sz]e|tell me about|show me|profile|evaluate|who is|what about|give me the rundown on|describe)\b", re.I)
_DRAFT_RE = re.compile(r"\b(draft|drafted|first overall|top pick|lottery|prospect ranking|mock draft)\b", re.I)
_TRANSACTION_RE = re.compile(r"\b(trade|trades|traded|signing|signed|free agency|waiver|waivers|buyout|extension|contract extension|transaction|transactions|roster move)\b", re.I)
_NEWS_RE = re.compile(r"\b(news|latest|update|what happened|this week|today|recent|headline|headlines)\b", re.I)
_EVENT_CONTEXT_RE = re.compile(r"\b(hire|hired|coach|coaching change|fired|affect|impact|signing|signed|trade|traded|free agency|rumor|rumour)\b", re.I)
_PROSPECT_RE = re.compile(r"\b(prospect|prospects|farm system|pipeline|draft class)\b", re.I)
_TEAM_RE = re.compile(r"\b(teams?|leaf\'?s|leafs|maple leaf\'?s|maple leafs|oilers|canadiens|habs|bruins|rangers|penguins|hurricanes|avalanche|stars|utah|blackhawks|red wings|sabres|senators|panthers|florida)\b", re.I)
_HISTORY_RE = re.compile(r"\b(ever|all[- ]time|history|historical|greatest|record|legacy|dynasty|won the stanley cup|stanley cup in)\b", re.I)
_PROJECTION_RE = re.compile(r"\b(project|projection|predict|likely|most likely|next season|breakout|future|outlook)\b", re.I)
_QUALITY_RE = re.compile(r"\b(how good|how strong|how valuable|right now|currently|current form|still good|elite|contender|cup threat|playoff team|weakness(?:es)?|weak spots?|flaws?|problems?|struggl(?:e|es|ed|ing)|hold(?:s)? .* back)\b", re.I)
_RULEBOOK_RE = re.compile(r"\b(cba|mou|rule|rules|salary cap|ltir|lti|waiver eligibility|minimum salary|contract variability|recall rule)\b", re.I)
_LEAGUE_RE = re.compile(r"\b(nhl|nba|nfl|mlb|fifa|uefa|mls|cfl|league)\b", re.I)


def classify_intent(question: str) -> IntentResult:
    """Classify a user prompt into Athena's canonical public intent types."""
    text = (question or "").strip()
    lower = text.lower()
    if not lower:
        return IntentResult(IntentType.UNKNOWN, 0.0, [], "Empty prompt.")

    matched: List[str] = []

    if _COMPARE_RE.search(text):
        matched.append("comparison")
        if _TEAM_RE.search(text) and not _PLAYER_COMMAND_RE.search(text):
            return IntentResult(IntentType.TEAM_COMPARISON, 0.82, matched, "Comparison language with team signal.")
        return IntentResult(IntentType.PLAYER_COMPARISON, 0.92, matched, "Comparison language detected.")

    if _DRAFT_RE.search(text):
        matched.append("draft")
        if _PROSPECT_RE.search(text):
            matched.append("prospect")
        return IntentResult(IntentType.DRAFT_ANALYSIS, 0.9, matched, "Draft/prospect selection language detected.")

    if _TRANSACTION_RE.search(text):
        matched.append("transaction")
        if _NEWS_RE.search(text):
            matched.append("news")
        return IntentResult(IntentType.TRANSACTION_SUMMARY, 0.89, matched, "Transaction/free-agency language detected.")

    if _RULEBOOK_RE.search(text):
        matched.append("rulebook")
        return IntentResult(IntentType.RULEBOOK_QUESTION, 0.86, matched, "Rulebook/CBA topic detected.")

    if _PROSPECT_RE.search(text):
        matched.append("prospect")
        return IntentResult(IntentType.PROSPECT_ANALYSIS, 0.84, matched, "Prospect/pipeline language detected.")

    if _PROJECTION_RE.search(text):
        matched.append("projection")
        return IntentResult(IntentType.PROJECTION, 0.78, matched, "Projection/outlook language detected.")

    if _HISTORY_RE.search(text):
        matched.append("history")
        return IntentResult(IntentType.HISTORICAL_QUESTION, 0.78, matched, "Historical language detected.")

    if _EVENT_CONTEXT_RE.search(text) and _TEAM_RE.search(text):
        matched.extend(["event_context", "team"])
        return IntentResult(IntentType.NEWS_SUMMARY, 0.76, matched, "Team event/impact language detected; route to Event Intelligence gap until live feeds are attached.")

    if _QUALITY_RE.search(text):
        matched.append("quality_analysis")
        if _TEAM_RE.search(text):
            matched.append("team")
            return IntentResult(IntentType.TEAM_ANALYSIS, 0.76, matched, "Quality/strength prompt with team signal detected.")
        return IntentResult(IntentType.PLAYER_ANALYSIS, 0.72, matched, "Quality/current-value prompt detected.")

    if _NEWS_RE.search(text) and _LEAGUE_RE.search(text):
        matched.extend(["news", "league"])
        return IntentResult(IntentType.NEWS_SUMMARY, 0.78, matched, "League news/update language detected.")

    if _PLAYER_COMMAND_RE.search(text):
        matched.append("player_command")
        return IntentResult(IntentType.PLAYER_ANALYSIS, 0.74, matched, "Player-style command detected.")

    # Short title-case/bare-name prompts are usually player profile requests in public mode.
    token_count = len(re.findall(r"[A-Za-zÀ-ÿ]+", text))
    if 1 <= token_count <= 3 and not text.endswith("?"):
        matched.append("bare_entity")
        return IntentResult(IntentType.PLAYER_PROFILE, 0.68, matched, "Short bare-entity prompt treated as profile request.")

    if _TEAM_RE.search(text):
        matched.append("team")
        return IntentResult(IntentType.TEAM_ANALYSIS, 0.62, matched, "Team signal detected.")

    return IntentResult(IntentType.GENERAL_DISCUSSION, 0.4, [], "No high-confidence public intent matched.")
