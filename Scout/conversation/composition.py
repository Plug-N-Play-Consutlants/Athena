"""Response Composition Engine for Scout acceptance surfaces.

This layer is the contract between Athena reasoning outputs and Scout display.
Reasoning modules may return conclusions, evidence, limitations, cards and raw
traces, but Scout's public surface must receive one clean user-facing answer.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List

from Experience.renderer import attach_experience_contract

PUBLIC_TEXT_KEYS = ("natural_language_response", "public_comment", "response_text", "scout_message", "engine_conclusion")
DIAGNOSTIC_KEYS = ("engine_conclusion", "observed_facts", "known_limitations", "raw_reasoning_output", "developer", "operation_result")

_INTERNAL_PATTERNS = [
    re.compile(r"\bAthena is combining\b.*?(?:\.|$)", re.IGNORECASE | re.DOTALL),
    re.compile(r"\b[A-Z][A-Za-z ]+ Intelligence \d+[A-Z]?\.\d+\b.*?(?:\.|$)", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bPIF Build \d+\b.*?(?:\.|$)", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bcurrent local evidence supports\b.*?(?:\.|$)", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bno longer assessed as a one-season stat line\b.*?(?:\.|$)", re.IGNORECASE | re.DOTALL),
]

_INTERNAL_LINE_PREFIXES = (
    "supporting evidence",
    "engine conclusion",
    "observed facts",
    "known limitations",
    "developer mode",
    "confidence:",
    "primary limitations:",
    "context impact",
    "contract context",
)

_LABEL_REPLACEMENTS = {
    "Athena Conclusion:": "Conclusion:",
    "Executive Comparison:": "Comparison:",
    "Public framing:": "Summary:",
    "nHL": "NHL",
    " are NHL franchise": " is an NHL franchise",
    "..": ".",
}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _first_text(answer: Dict[str, Any], keys: Iterable[str] = PUBLIC_TEXT_KEYS) -> str:
    for key in keys:
        text = _clean_text(answer.get(key))
        if text:
            return text
    return _clean_text(answer.get("title"))


def _as_list(value: Any, limit: int | None = None) -> List[Any]:
    if not isinstance(value, list):
        return []
    return value[:limit] if limit is not None else list(value)


def _clean_public_text(text: str) -> str:
    text = _clean_text(text)
    if not text:
        return ""
    for pattern in _INTERNAL_PATTERNS:
        text = pattern.sub("", text)
    for old, new in _LABEL_REPLACEMENTS.items():
        text = text.replace(old, new)
    kept: List[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if kept and kept[-1] != "":
                kept.append("")
            continue
        lower = line.lower()
        if any(lower.startswith(prefix) for prefix in _INTERNAL_LINE_PREFIXES):
            continue
        if " evidence available:" in lower:
            continue
        if "module" in lower and "execut" in lower:
            continue
        kept.append(line)
    cleaned = "\n".join(kept).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = cleaned.replace(" .", ".")
    return cleaned.strip()


def _card_map(answer: Dict[str, Any]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for card in answer.get("cards") or []:
        if isinstance(card, dict):
            label = _clean_text(card.get("label"))
            value = _clean_text(card.get("value"))
            if label and value:
                result[label.lower()] = value
    return result


def _compose_player_public(answer: Dict[str, Any], candidate: str) -> str:
    title = _clean_text(answer.get("title")) or "Player analysis"
    cards = _card_map(answer)
    facts = [_clean_public_text(item) for item in _as_list(answer.get("observed_facts"), 10)]
    facts = [item for item in facts if item]
    lines: List[str] = []
    if candidate:
        first = candidate.split("\n", 1)[0].strip()
        if first and len(first) > 40:
            lines.append(first)
    if not lines:
        role = cards.get("role") or cards.get("public value") or cards.get("career tier")
        band = cards.get("production band")
        ppg = cards.get("ppg") or cards.get("3-year ppg")
        pieces = []
        if role:
            pieces.append(f"profiles as {role.lower()}")
        if band:
            pieces.append(f"with {band.lower()} production")
        if ppg:
            pieces.append(f"around {ppg} points per game in the available sample")
        if pieces:
            lines.append(f"{title} {' '.join(pieces)}.")
    for fact in facts:
        lower = fact.lower()
        if any(term in lower for term in ["identity:", "career legacy", "current value", "career baselines", "trend analysis", "organizational importance", "historical context"]):
            lines.append(fact)
        elif len(lines) < 4 and not any(bad in lower for bad in ["evidence", "build", "module"]):
            lines.append(fact)
    if candidate and len(candidate.splitlines()) > 1:
        for block in candidate.split("\n\n"):
            clean = _clean_public_text(block)
            if clean and clean not in lines and not clean.lower().startswith("executive summary"):
                lines.append(clean)
    if not lines:
        lines.append(title)
    return "\n\n".join(lines[:8])


def _compose_team_public(answer: Dict[str, Any], candidate: str) -> str:
    candidate = _clean_public_text(candidate)
    if candidate and not candidate.lower().startswith("executive summary:"):
        return candidate
    facts = [_clean_public_text(item) for item in _as_list(answer.get("observed_facts"), 10)]
    facts = [item for item in facts if item]
    title = _clean_text(answer.get("title")) or "Team analysis"
    lines = [title]
    for fact in facts[:6]:
        lines.append(fact)
    return "\n\n".join(lines)


def _compose_public_comment(answer: Dict[str, Any]) -> str:
    candidate = _clean_public_text(_first_text(answer))
    intent = _clean_text(answer.get("intent")).lower()
    if intent in {"player_analysis", "public_player_profile"}:
        return _compose_player_public(answer, candidate)
    if intent in {"public_team_profile", "public_team_comparison", "public_analytical_route"}:
        return _compose_team_public(answer, candidate)
    return candidate or _clean_text(answer.get("title")) or "Scout response"


def compose_answer_payload(answer: Dict[str, Any]) -> Dict[str, Any]:
    """Return an answer with explicit public and diagnostic surfaces."""
    if not isinstance(answer, dict):
        public_text = _clean_public_text(answer)
        return attach_experience_contract({
            "title": "Scout response",
            "public_comment": public_text,
            "natural_language_response": public_text,
            "diagnostics": {},
            "display_contract": "athena_response",
        })

    diagnostics = {
        "engine_conclusion": _clean_text(answer.get("engine_conclusion")),
        "observed_facts": _as_list(answer.get("observed_facts"), 12),
        "known_limitations": _as_list(answer.get("known_limitations"), 12),
        "raw_reasoning_output": _clean_text(answer.get("raw_reasoning_output")) or _clean_text((answer.get("developer") or {}).get("raw_reasoning_output") if isinstance(answer.get("developer"), dict) else ""),
        "developer": answer.get("developer") if isinstance(answer.get("developer"), dict) else {},
        "operation_result": answer.get("operation_result") or ((answer.get("developer") or {}).get("operation_result") if isinstance(answer.get("developer"), dict) else None),
    }

    composed = dict(answer)
    public_comment = _compose_public_comment(composed)
    composed["public_comment"] = public_comment
    # Collapse legacy answer aliases onto the public surface so older consumers
    # cannot accidentally render stale diagnostic/fallback prose.
    composed["natural_language_response"] = public_comment
    composed["response_text"] = public_comment
    composed["scout_message"] = public_comment
    composed["diagnostics"] = diagnostics
    composed["display_contract"] = "athena_response"
    composed["diagnostic_keys"] = list(DIAGNOSTIC_KEYS)
    return attach_experience_contract(composed)


def public_debug_summary(answer: Dict[str, Any]) -> Dict[str, Any]:
    composed = compose_answer_payload(answer)
    diagnostics = composed.get("diagnostics") if isinstance(composed.get("diagnostics"), dict) else {}
    return {
        "title": composed.get("title", "Scout response"),
        "intent": composed.get("intent", ""),
        "public_comment": composed.get("public_comment", ""),
        "confidence": composed.get("confidence"),
        "diagnostics": {
            "engine_conclusion": diagnostics.get("engine_conclusion", ""),
            "observed_facts": _as_list(diagnostics.get("observed_facts"), 12),
            "known_limitations": _as_list(diagnostics.get("known_limitations"), 12),
        },
    }
