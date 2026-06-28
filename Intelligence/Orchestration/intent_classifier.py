"""Intent-first classifier for Athena orchestration.

This classifier is deliberately deterministic in v0.5.6.0.0.  It sits above
legacy entity-first routing and emits analytical objectives that can drive an
ExecutionPlan.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Dict, List

from .intent_taxonomy import IntentType, definition_for


_ENTITY_TEAM_RE = re.compile(r"\b(leafs|maple leafs|toronto|oilers|edmonton|red wings|detroit|panthers|florida|hurricanes|canes|avalanche|stars|blackhawks|sharks)\b", re.I)
_COMPARE_RE = re.compile(r"\b(vs\.?|versus|compare|better than|who is better|which is better)\b", re.I)
_IMPACT_RE = re.compile(r"\b(how does|how would|what does|impact|improve|fit|change|affect|helps?|upgrade|bring(?:s)? to)\b", re.I)
_ROSTER_RE = re.compile(r"\b(roster construction|lineup|lines?|depth chart|special teams|power play|penalty kill|deployment|weakness(?:es)?|weak spots?|holes?)\b", re.I)
_PROJECTION_RE = re.compile(r"\b(project|projection|future|outlook|next season|next \d+ years|over the next|development path|ceiling|floor)\b", re.I)
_RULE_RE = re.compile(r"\b(rule|rules|scoring|keeper|keepers|contract|contracts|eligibility|salary cap|ltir|waiver|waivers|settings)\b", re.I)
_FANTASY_RE = re.compile(r"\b(my league|fantasy|fantrax|keeper|keepers|waiver|draft prep|trade offer|roster)\b", re.I)
_TRADE_RE = re.compile(r"\b(trade|trades|trading|offer|acquire|move)\b", re.I)
_DRAFT_RE = re.compile(r"\b(draft|drafted|pick|prospect|lottery|first overall|1st overall)\b", re.I)
_CAUSAL_RE = re.compile(r"\b(why|how come|what is holding|what holds|reason|because|explain)\b", re.I)
_PROFILE_RE = re.compile(r"^\s*(tell me about|who is|what is|profile|describe|give me the rundown on)\b", re.I)


@dataclass(frozen=True)
class ClassifiedIntent:
    primary_intent: IntentType
    confidence: float
    secondary_intents: List[IntentType] = field(default_factory=list)
    matched_signals: List[str] = field(default_factory=list)
    rationale: str = ""

    @property
    def family(self) -> str:
        return definition_for(self.primary_intent).family.value

    def to_dict(self) -> Dict[str, object]:
        return {
            "primary_intent": self.primary_intent.value,
            "family": self.family,
            "confidence": self.confidence,
            "secondary_intents": [intent.value for intent in self.secondary_intents],
            "matched_signals": list(self.matched_signals),
            "rationale": self.rationale,
        }


def classify_request_intent(question: str, mode: str = "public") -> ClassifiedIntent:
    text = (question or "").strip()
    lower = text.lower()
    selected_mode = (mode or "public").strip().lower()
    if not lower:
        return ClassifiedIntent(IntentType.UNKNOWN, 0.0, rationale="Empty prompt.")

    signals: List[str] = []
    secondary: List[IntentType] = []
    has_team = bool(_ENTITY_TEAM_RE.search(text))
    has_fantasy = selected_mode == "fantasy" or bool(_FANTASY_RE.search(text))

    if _COMPARE_RE.search(text):
        signals.append("comparison")
        primary = IntentType.TEAM_COMPARISON if has_team and not _PROFILE_RE.search(text) else IntentType.PLAYER_COMPARISON
        return ClassifiedIntent(primary, 0.92, matched_signals=signals, rationale="Comparison language is an explicit analytical objective.")

    if has_fantasy and _TRADE_RE.search(text):
        signals.extend(["fantasy", "trade"])
        return ClassifiedIntent(IntentType.FANTASY_TRADE_ANALYSIS, 0.9, [IntentType.ROSTER_CONSTRUCTION], signals, "Fantasy trade language requires league-aware decision support.")

    if has_fantasy and _DRAFT_RE.search(text):
        signals.extend(["fantasy", "draft"])
        return ClassifiedIntent(IntentType.FANTASY_DRAFT_ANALYSIS, 0.88, [IntentType.PLAYER_PROJECTION], signals, "Fantasy draft language requires league-context planning.")

    if _RULE_RE.search(text) and not _IMPACT_RE.search(text):
        signals.append("rules")
        return ClassifiedIntent(IntentType.LEAGUE_RULES, 0.84, matched_signals=signals, rationale="Rules/settings language detected without broader impact phrasing.")

    if _IMPACT_RE.search(text) and has_team:
        signals.extend(["impact", "team_context"])
        if _PROJECTION_RE.search(text):
            signals.append("projection")
            secondary.append(IntentType.PLAYER_PROJECTION)
        if _ROSTER_RE.search(text):
            signals.append("roster_construction")
            secondary.append(IntentType.ROSTER_CONSTRUCTION)
        if _DRAFT_RE.search(text):
            signals.append("draft_or_prospect")
            secondary.append(IntentType.PLAYER_PROJECTION)
        return ClassifiedIntent(IntentType.ORGANIZATIONAL_IMPACT, 0.89, secondary, signals, "Impact phrasing plus team context means entities are inputs to an organizational analysis.")

    if _ROSTER_RE.search(text) and has_team:
        signals.extend(["roster_construction", "team_context"])
        return ClassifiedIntent(IntentType.ROSTER_CONSTRUCTION, 0.82, [IntentType.TEAM_PROFILE], signals, "Roster/deployment weakness language requires structure analysis.")

    if _PROJECTION_RE.search(text):
        signals.append("projection")
        primary = IntentType.TEAM_PROJECTION if has_team else IntentType.PLAYER_PROJECTION
        return ClassifiedIntent(primary, 0.78, matched_signals=signals, rationale="Projection/outlook language detected.")

    if _CAUSAL_RE.search(text):
        signals.append("causal_explanation")
        secondary = [IntentType.TEAM_PROFILE] if has_team else [IntentType.PLAYER_PROFILE]
        return ClassifiedIntent(IntentType.CAUSAL_EXPLANATION, 0.76, secondary, signals, "The prompt asks for causal explanation rather than description.")

    if _PROFILE_RE.search(text):
        signals.append("profile_command")
        primary = IntentType.TEAM_PROFILE if has_team else IntentType.PLAYER_PROFILE
        return ClassifiedIntent(primary, 0.74, matched_signals=signals, rationale="Profile-style command detected.")

    if has_team:
        signals.append("team_entity")
        return ClassifiedIntent(IntentType.TEAM_PROFILE, 0.66, matched_signals=signals, rationale="Team entity detected without stronger analytical objective.")

    token_count = len(re.findall(r"[A-Za-zÀ-ÿ]+", text))
    if 1 <= token_count <= 3:
        signals.append("short_bare_entity")
        return ClassifiedIntent(IntentType.PLAYER_PROFILE, 0.64, matched_signals=signals, rationale="Short bare entity treated as player profile until resolved otherwise.")

    return ClassifiedIntent(IntentType.UNKNOWN, 0.35, matched_signals=[], rationale="No confident orchestration intent matched.")
