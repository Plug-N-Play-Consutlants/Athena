"""Response helpers for Scout Alpha."""

from __future__ import annotations

from typing import Any, Dict, List

from Scout.conversation.composition import compose_answer_payload


def _natural_language_response(title: str, engine_conclusion: str, observed_facts: List[str], known_limitations: List[str]) -> str:
    """Create a safe public fallback from Athena evidence.

    Diagnostic evidence belongs in the diagnostics surface, not the public
    answer. Earlier Scout builds appended observed facts and limitations here,
    which made public answers read like trace output. When a route has not
    provided a purpose-built narrative, use the conclusion only.
    """
    return str(engine_conclusion or title or "Scout response").strip()


def response(
    intent: str,
    title: str,
    engine_conclusion: str,
    observed_facts: List[str] | None = None,
    known_limitations: List[str] | None = None,
    developer: Dict[str, Any] | None = None,
    confidence: float | None = None,
    cards: List[Dict[str, Any]] | None = None,
    natural_language_response: str | None = None,
) -> Dict[str, Any]:
    facts = observed_facts or []
    limitations = known_limitations or []
    natural = str(natural_language_response or "").strip() or _natural_language_response(title, engine_conclusion, facts, limitations)
    return compose_answer_payload({
        "intent": intent,
        "title": title,
        "natural_language_response": natural,
        "engine_conclusion": engine_conclusion,
        "observed_facts": facts,
        "known_limitations": limitations,
        "confidence": confidence,
        "cards": cards or [],
        "developer": developer or {},
    })


def developer_info(
    intent: str,
    context_loaded: List[str],
    knowledge_used: List[str] | None = None,
    intelligence_used: List[str] | None = None,
    files_read: List[str] | None = None,
    missing: List[str] | None = None,
) -> Dict[str, Any]:
    return {
        "intent": intent,
        "context_loaded": context_loaded,
        "knowledge_used": knowledge_used or [],
        "intelligence_used": intelligence_used or [],
        "files_read": files_read or [],
        "missing_or_limited": missing or [],
    }
