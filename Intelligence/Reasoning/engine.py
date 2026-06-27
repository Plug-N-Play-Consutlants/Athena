"""Cross-sport reasoning orchestration.

This module starts from the last validated explainable pipeline and adds a
sport-neutral reasoning engine. It does not replace the lower layers; it wraps
route, evidence, ambiguity, and confidence into one deterministic result.
"""
from __future__ import annotations

from typing import Any, Iterable, Tuple

from .adapters import seed_reasoning_adapter_registry, adapter_registry_diagnostics
from Knowledge.Events.live_sources import live_event_source_summary

from .models import (
    CROSS_SPORT_REASONING_VERSION,
    AmbiguityCandidate,
    AmbiguityResolution,
    CrossSportComparison,
    CrossSportReasoningResult,
    FusedEvidence,
)


def _safe_route(question: str, mode: str = "public") -> Any | None:
    try:
        from Knowledge.Intelligence.Routing.multi_sport_router import route_multi_sport_query
        return route_multi_sport_query(question, mode=mode)
    except Exception:
        return None


def _safe_explain(question: str, mode: str = "public") -> Any | None:
    try:
        from Intelligence.Pipeline import execute_explainable_intelligence
        return execute_explainable_intelligence(question, mode=mode)
    except Exception:
        return None


def _fuse_from_route(route: Any | None, explanation: Any | None) -> Tuple[FusedEvidence, ...]:
    fused: list[FusedEvidence] = []
    try:
        live_summary = live_event_source_summary()
    except Exception:
        live_summary = {}
    if route is not None:
        for item in getattr(route, "evidence", ()):
            fused.append(FusedEvidence("routing", "Routing evidence", str(item), 0.58, 0.9, "routing"))
        for entity in getattr(route, "entity_labels", ()):
            fused.append(FusedEvidence("identity", "Resolved entity", str(entity), 0.72, 1.1, "identity"))
        for module in getattr(route, "intelligence_modules", ()):
            fused.append(FusedEvidence("capability", "Selected module", str(module), 0.66, 1.0, "capability"))
        for source in getattr(route, "capability_sources", ()):
            fused.append(FusedEvidence("evidence_source", "Available source", str(source), 0.60, 0.8, "source"))
        intent = str(getattr(route, "intent", "") or "")
        sport = str(getattr(route, "sport", "multi") or "multi")
        if live_summary and intent in {"event_context", "player_assessment", "team_assessment", "general"}:
            for feed in live_summary.get("feeds", []):
                if not isinstance(feed, dict):
                    continue
                feed_sport = str(feed.get("sport", "multi") or "multi")
                if feed_sport not in {sport, "multi"}:
                    continue
                detail = f"{feed.get('display_name')} ({feed.get('connector_type')}; opt-in network)"
                fused.append(FusedEvidence("live_sources", "Registered live event source", detail, 0.62, 0.85, "live_source", feed))
    if explanation is not None:
        try:
            evidence_items = explanation.evidence.all_items()
        except Exception:
            evidence_items = ()
        for item in evidence_items:
            fused.append(FusedEvidence(getattr(item, "source", "explainability"), getattr(item, "label", "Evidence"), getattr(item, "detail", ""), getattr(item, "confidence", 0.5), 1.0, "explainability", getattr(item, "payload", {}) or {}))
    # Stable de-duplication by visible content.
    seen: set[tuple[str, str, str]] = set()
    unique: list[FusedEvidence] = []
    for item in fused:
        key = (item.source, item.label, item.detail)
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return tuple(unique)


def _resolve_ambiguity(route: Any | None) -> AmbiguityResolution:
    if route is None:
        return AmbiguityResolution("unresolved", notes=("No route was available for ambiguity resolution.",))
    labels = tuple(getattr(route, "entity_labels", ()) or ())
    ids = tuple(getattr(route, "entities", ()) or ())
    candidates = tuple(
        AmbiguityCandidate(
            entity_id=str(ids[index]) if index < len(ids) else str(label),
            label=str(label),
            sport=str(getattr(route, "sport", "") or ""),
            league=str(getattr(route, "league", "") or ""),
            confidence=min(0.95, float(getattr(route, "confidence", 0.55))),
        )
        for index, label in enumerate(labels)
    )
    if getattr(route, "ambiguity", False):
        return AmbiguityResolution("ambiguous", candidates=candidates, notes=("Multiple candidates require clarification before high-confidence reasoning.",))
    if candidates:
        return AmbiguityResolution("resolved", selected=(candidates[0],), candidates=candidates, notes=("Entity selected from identity routing context.",))
    return AmbiguityResolution("none", notes=("No canonical entity was resolved.",))


def _comparison_from_route(route: Any | None) -> CrossSportComparison:
    if route is None:
        return CrossSportComparison(False, notes=("Routing unavailable.",))
    intent = str(getattr(route, "intent", "") or "")
    labels = tuple(getattr(route, "entity_labels", ()) or ())
    modules = tuple(getattr(route, "intelligence_modules", ()) or ())
    enabled = intent == "comparison" or len(labels) > 1
    basis = tuple(item for item in ("identity", "knowledge", "historical", "events") if item in " ".join(modules + tuple(getattr(route, "capability_sources", ()) or ())))
    if enabled:
        return CrossSportComparison(True, basis=basis or ("identity", "knowledge"), notes=("Comparison is framed through normalized evidence, not direct stat translation.",))
    return CrossSportComparison(False, notes=("Request did not require cross-sport or multi-entity comparison.",))


def _confidence(route: Any | None, evidence: Iterable[FusedEvidence], ambiguity: AmbiguityResolution, adapter_found: bool) -> float:
    base = float(getattr(route, "confidence", 0.35) if route is not None else 0.25)
    ev = tuple(evidence)
    if ev:
        weighted = sum(item.weighted_confidence() for item in ev) / max(1.0, sum(max(0.0, item.weight) for item in ev))
        base = (base * 0.55) + (weighted * 0.45)
    if adapter_found:
        base += 0.05
    if ambiguity.ambiguous:
        base -= 0.12
    elif ambiguity.status == "resolved":
        base += 0.04
    return round(max(0.0, min(0.95, base)), 4)


def reason_cross_sport_query(question: str, mode: str = "public") -> CrossSportReasoningResult:
    route = _safe_route(question, mode=mode)
    explanation = _safe_explain(question, mode=mode)
    registry = seed_reasoning_adapter_registry()
    adapter = registry.resolve(
        sport=str(getattr(route, "sport", "") or ""),
        league=str(getattr(route, "league", "") or ""),
        intent=str(getattr(route, "intent", "general") or "general"),
    ) if route is not None else None
    fused = _fuse_from_route(route, explanation)
    ambiguity = _resolve_ambiguity(route)
    comparison = _comparison_from_route(route)
    limitations: list[str] = []
    if route is None:
        limitations.append("Multi-sport route unavailable.")
    if adapter is None:
        limitations.append("No sport-specific adapter was selected.")
    if not fused:
        limitations.append("No fused evidence was available.")
    if ambiguity.ambiguous:
        limitations.append("Entity ambiguity remains unresolved.")
    confidence = _confidence(route, fused, ambiguity, adapter_found=adapter is not None)
    steps = (
        {"step": "route", "status": "pass" if route is not None else "fail", "detail": getattr(route, "route", "unavailable") if route is not None else "routing unavailable"},
        {"step": "adapter", "status": "pass" if adapter is not None else "warn", "detail": adapter.label if adapter is not None else "no adapter selected"},
        {"step": "evidence_fusion", "status": "pass" if fused else "warn", "detail": f"{len(fused)} fused evidence items"},
        {"step": "ambiguity", "status": "warn" if ambiguity.ambiguous else "pass", "detail": ambiguity.status},
        {"step": "comparison", "status": "pass", "detail": "enabled" if comparison.enabled else "not required"},
        {"step": "confidence", "status": "pass", "detail": str(confidence)},
    )
    status = "pass" if route is not None and fused and not ambiguity.ambiguous else "warn"
    return CrossSportReasoningResult(
        question=str(question or ""),
        route=str(getattr(route, "route", "unavailable") if route is not None else "unavailable"),
        intent=str(getattr(route, "intent", "unknown") if route is not None else "unknown"),
        sport=str(getattr(route, "sport", "") if route is not None else ""),
        league=str(getattr(route, "league", "") if route is not None else ""),
        adapter=adapter.label if adapter is not None else "",
        modules=tuple(getattr(route, "intelligence_modules", ()) if route is not None else ()),
        fused_evidence=fused,
        ambiguity=ambiguity,
        comparison=comparison,
        reasoning_steps=steps,
        confidence=confidence,
        status=status,
        limitations=tuple(limitations),
    )


def studio_reasoning_diagnostics() -> dict:
    samples = (
        "Compare Auston Matthews vs Connor McDavid in the NHL",
        "Summarize Blue Jays injuries",
        "Tell me about the Toronto Raptors",
        "Who is Sebastian Aho?",
    )
    results = [reason_cross_sport_query(sample).to_dict() for sample in samples]
    return {
        "panel": "cross_sport_reasoning",
        "version": CROSS_SPORT_REASONING_VERSION,
        "status": "pass" if all(result["reasoning_steps"] for result in results) else "warn",
        "adapter_registry": adapter_registry_diagnostics(),
        "sample_count": len(results),
        "results": results,
        "supports": [
            "cross-sport reasoning orchestration",
            "sport adapter registry",
            "evidence fusion",
            "entity ambiguity resolution",
            "cross-sport comparison framing",
        ],
    }


__all__ = [
    "reason_cross_sport_query",
    "studio_reasoning_diagnostics",
]
