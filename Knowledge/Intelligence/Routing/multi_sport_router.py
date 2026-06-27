"""Sport-aware Scout routing helpers for Athena v0.5.3.3.0.

This layer is intentionally deterministic. It does not replace the deeper public
or fantasy reasoning engines; it classifies query sport/league/entity context so
Scout can avoid cross-sport ambiguity and surface provider/source routing
metadata through explainability.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Sequence

try:
    from Knowledge.Identity import IdentityEntity, seed_identity_registry
except Exception:  # pragma: no cover - partial installs should fail gracefully
    IdentityEntity = Any  # type: ignore
    seed_identity_registry = None  # type: ignore

try:
    from Intelligence.Foundation import select_intelligence_modules, studio_intelligence_diagnostics
except Exception:  # pragma: no cover - older partial installs degrade gracefully
    select_intelligence_modules = None  # type: ignore
    studio_intelligence_diagnostics = None  # type: ignore

try:
    from Intelligence.Pipeline import execute_explainable_intelligence, studio_explainability_diagnostics
except Exception:  # pragma: no cover
    execute_explainable_intelligence = None  # type: ignore
    studio_explainability_diagnostics = None  # type: ignore

try:
    from Sports import seed_sport_registry
except Exception:  # pragma: no cover
    seed_sport_registry = None  # type: ignore

try:
    from Intelligence.Reasoning import reason_cross_sport_query, studio_reasoning_diagnostics
except Exception:  # pragma: no cover
    reason_cross_sport_query = None  # type: ignore
    studio_reasoning_diagnostics = None  # type: ignore

SPORT_HINTS: dict[str, str] = {
    "nhl": "hockey",
    "hockey": "hockey",
    "leafs": "hockey",
    "maple leafs": "hockey",
    "oilers": "hockey",
    "nba": "basketball",
    "basketball": "basketball",
    "raptors": "basketball",
    "mlb": "baseball",
    "baseball": "baseball",
    "blue jays": "baseball",
    "jays": "baseball",
    "nfl": "football",
    "football": "football",
    "bills": "football",
    "soccer": "soccer",
    "uefa": "soccer",
}

LEAGUE_HINTS: dict[str, str] = {
    "nhl": "NHL",
    "nba": "NBA",
    "mlb": "MLB",
    "nfl": "NFL",
    "uefa": "UEFA",
}

INTENT_HINTS: dict[str, str] = {
    "compare": "comparison",
    "versus": "comparison",
    " vs ": "comparison",
    "profile": "profile",
    "who is": "profile",
    "tell me about": "profile",
    "summarize": "summary",
    "summary": "summary",
    "injury": "event_context",
    "trade": "event_context",
    "transaction": "event_context",
    "schedule": "event_context",
    "game": "event_context",
}

@dataclass(frozen=True)
class ScoutRoute:
    route: str
    sport: str = ""
    league: str = ""
    intent: str = "general"
    entities: tuple[str, ...] = ()
    entity_labels: tuple[str, ...] = ()
    ambiguity: bool = False
    allowed_sources: tuple[str, ...] = ()
    blocked_sources: tuple[str, ...] = ()
    confidence: float = 0.45
    evidence: tuple[str, ...] = ()
    intelligence_modules: tuple[str, ...] = ()
    capability_sources: tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _normal(text: str) -> str:
    return " ".join(str(text or "").lower().replace("?", " ").replace(",", " ").split())


def _detect_intent(text: str) -> str:
    padded = f" {_normal(text)} "
    # Event context terms must win over wrappers such as "summarize" so
    # prompts like "Summarize Blue Jays injuries" route to event intelligence.
    for hint in ("injury", "injuries", "trade", "transaction", "schedule", "game"):
        if f" {hint} " in padded or hint in padded:
            return "event_context"
    for hint, intent in INTENT_HINTS.items():
        if hint in padded:
            return intent
    return "general"


def _detect_sport_and_league(text: str) -> tuple[str, str, list[str]]:
    padded = f" {_normal(text)} "
    sport = ""
    league = ""
    evidence: list[str] = []
    if seed_sport_registry is not None:
        try:
            registry = seed_sport_registry()
            for definition in registry.all_sports():
                if f" {definition.sport_id} " in padded or f" {definition.display_name.lower()} " in padded:
                    sport = definition.sport_id
                    evidence.append(f"sport registry: {definition.display_name} -> {sport}")
                    break
                for candidate_league in definition.primary_leagues:
                    if f" {candidate_league.lower()} " in padded:
                        sport = definition.sport_id
                        league = candidate_league
                        evidence.append(f"sport registry league: {candidate_league} -> {sport}")
                        break
                if sport:
                    break
        except Exception:
            pass
    if not sport:
        for hint, value in SPORT_HINTS.items():
            if f" {hint} " in padded:
                sport = value
                evidence.append(f"sport hint: {hint} -> {value}")
                break
    if not league:
        for hint, value in LEAGUE_HINTS.items():
            if f" {hint} " in padded:
                league = value
                evidence.append(f"league hint: {hint} -> {value}")
                break
    return sport, league, evidence


def _entity_phrases(text: str) -> list[str]:
    raw = str(text or "").strip()
    lowered = _normal(raw)
    phrases = [raw]
    for prefix in ("compare", "profile", "who is", "tell me about", "show me", "analyze", "analyse", "summarize"):
        if lowered.startswith(prefix):
            candidate = raw[len(prefix):].strip(" :-.?")
            if candidate:
                phrases.append(candidate)
    splitters = [" vs ", " versus ", " and ", " against "]
    for splitter in splitters:
        if splitter in f" {lowered} ":
            for part in re.split(splitter.strip(), raw, flags=re.IGNORECASE):
                cleaned = part.strip(" :-.?")
                if cleaned:
                    phrases.append(cleaned)
    return list(dict.fromkeys(phrases))


def _resolve_entities(text: str, sport: str = "", league: str = "") -> tuple[list[Any], bool, list[str]]:
    if seed_identity_registry is None:
        return [], False, ["identity registry unavailable"]
    registry = seed_identity_registry()
    matches: list[Any] = []
    evidence: list[str] = []
    for phrase in _entity_phrases(text):
        # Try exact phrase first, then type-specific searches so teams and players both surface.
        found = list(registry.search_name(phrase, sport=sport, league=league))
        if found:
            evidence.append(f"entity phrase: {phrase} -> {', '.join(e.entity_id for e in found[:3])}")
        for entity in found:
            if entity.entity_id not in {m.entity_id for m in matches}:
                matches.append(entity)
    ambiguous = len({m.entity_id for m in matches}) > 1 and len({_normal(m.canonical_name) for m in matches}) == 1
    return matches, ambiguous, evidence


def route_multi_sport_query(question: str, mode: str = "public") -> ScoutRoute:
    text = str(question or "")
    sport, league, evidence = _detect_sport_and_league(text)
    entities, ambiguous, entity_evidence = _resolve_entities(text, sport=sport, league=league)
    evidence.extend(entity_evidence)
    if not sport and entities:
        sport = getattr(entities[0], "sport", "") or ""
        evidence.append(f"sport inferred from entity: {sport}")
    if not league and entities:
        league = getattr(entities[0], "league", "") or ""
        evidence.append(f"league inferred from entity: {league}")
    intent = _detect_intent(text)
    route = "multi_sport_public"
    if ambiguous:
        route = "multi_sport_disambiguation"
    elif intent == "comparison":
        route = "multi_sport_comparison"
    elif intent in {"profile", "summary"} and entities:
        route = "multi_sport_entity_profile"
    elif intent == "event_context":
        route = "multi_sport_event_context"
    elif sport or league:
        route = "multi_sport_context"
    source_prefix = league.lower() if league else sport
    allowed = tuple(x for x in (source_prefix, "public_knowledge", "event_intelligence", "identity_registry") if x)
    blocked = ("fantasy_owner_context",) if (mode or "").lower() == "public" else ()
    modules = tuple()
    capability_sources = tuple()
    if select_intelligence_modules is not None:
        entity_type = getattr(entities[0], "entity_type", "") if entities else ""
        selected = select_intelligence_modules(intent=intent, sport=sport, entity_type=entity_type)
        modules = tuple(module.module_id for module in selected)
        capability_sources = tuple(sorted({source for module in selected for source in module.evidence_sources}))
        if modules:
            evidence.append("intelligence modules: " + ", ".join(modules))
    confidence = 0.55 + (0.15 if sport else 0.0) + (0.1 if league else 0.0) + (0.1 if entities else 0.0) + (0.05 if modules else 0.0)
    return ScoutRoute(
        route=route,
        sport=sport,
        league=league,
        intent=intent,
        entities=tuple(getattr(e, "entity_id", "") for e in entities),
        entity_labels=tuple(getattr(e, "canonical_name", "") for e in entities),
        ambiguity=ambiguous,
        allowed_sources=allowed,
        blocked_sources=blocked,
        confidence=min(confidence, 0.95),
        evidence=tuple(evidence or ["no sport-specific route evidence detected"]),
        intelligence_modules=modules,
        capability_sources=capability_sources,
    )


def studio_route_diagnostics(samples: Sequence[str] | None = None) -> Dict[str, Any]:
    examples = samples or (
        "Compare Auston Matthews vs Connor McDavid in the NHL",
        "Tell me about the Toronto Raptors",
        "Summarize Blue Jays injuries",
        "Who is Sebastian Aho?",
    )
    routes = [route_multi_sport_query(sample).to_dict() for sample in examples]
    return {
        "version": "0.5.5.2.0",
        "intelligence": studio_intelligence_diagnostics() if studio_intelligence_diagnostics else {},
        "explainability": studio_explainability_diagnostics() if studio_explainability_diagnostics else {},
        "reasoning": studio_reasoning_diagnostics() if studio_reasoning_diagnostics else {},
        "sample_count": len(routes),
        "routes": routes,
        "supports": ["sport-aware routing", "source routing metadata", "identity ambiguity flags", "public/fantasy context separation", "cross-sport reasoning diagnostics"],
    }

__all__ = ["ScoutRoute", "route_multi_sport_query", "studio_route_diagnostics"]
