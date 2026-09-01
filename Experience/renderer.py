"""Experience Layer render contract builders.

This module converts existing Scout/Athena answer dictionaries into a canonical
AthenaResponse. It deliberately avoids graph/provider assumptions so Scout can
become a renderer instead of a layout engine.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

from Experience.player import build_player_experience_section, _coverage_categories, _public_limitations

from Experience.models import (
    AthenaResponse,
    ConfidenceSummary,
    EvidenceItem,
    ExperienceMetadata,
    PlayerIdentity,
    StatBox,
    UISection,
)

PLAYER_PROFILE_INTENTS = {
    "player_analysis",
    "public_player_profile",
    "public_player_explainability",
    "public_player_comparison_subject",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _as_list(value: Any, limit: Optional[int] = None) -> List[Any]:
    if not isinstance(value, list):
        return []
    return value[:limit] if limit is not None else list(value)


def _card_map(answer: Dict[str, Any]) -> Dict[str, str]:
    cards: Dict[str, str] = {}
    for card in answer.get("cards") or []:
        if not isinstance(card, dict):
            continue
        label = _text(card.get("label") or card.get("title") or card.get("name"))
        value = _text(card.get("value") or card.get("summary") or card.get("text"))
        if label and value:
            cards[label.lower()] = value
    return cards


def _confidence_label(score: Any) -> str:
    try:
        value = float(score)
    except (TypeError, ValueError):
        return "Unknown"
    if value >= 0.8:
        return "High"
    if value >= 0.55:
        return "Moderate"
    if value > 0:
        return "Low"
    return "Unknown"


def _extract_jersey_number(answer: Dict[str, Any], cards: Dict[str, str]) -> str:
    explicit = (
        _text(answer.get("jersey_number"))
        or _text(answer.get("player_number"))
        or _text(cards.get("jersey number"))
        or _text(cards.get("number"))
        or _text(cards.get("#"))
    )
    if explicit:
        return explicit.lstrip("#")
    for source in (_text(answer.get("subtitle")), _text(answer.get("title")), _text(answer.get("natural_language_response"))):
        match = re.search(r"(?:^|\s)#\s?(\d{1,3})(?:\s|$|[•,])", source)
        if match:
            return match.group(1)
    return ""


def _extract_player_name(answer: Dict[str, Any]) -> str:
    player = answer.get("player") if isinstance(answer.get("player"), dict) else {}
    return (
        _text(player.get("full_name"))
        or _text(player.get("name"))
        or _text(answer.get("player_name"))
        or _text(answer.get("subject"))
        or _text(answer.get("title"))
        or "Player"
    )


def _assessment_badges(answer: Dict[str, Any], cards: Dict[str, str]) -> List[str]:
    badges = answer.get("assessment_badges")
    if isinstance(badges, list) and badges:
        return [_text(item).upper() for item in badges if _text(item)][:3]
    candidates: List[str] = []
    for key in ("career tier", "public value", "role", "trajectory", "trend"):
        value = _text(cards.get(key))
        if value:
            candidates.append(value)
    if not candidates:
        confidence = _confidence_label(answer.get("confidence"))
        if confidence != "Unknown":
            candidates.append(f"{confidence} Confidence")
    normalized: List[str] = []
    for item in candidates:
        token = re.sub(r"[^A-Za-z0-9 +\-/]", "", item).strip().upper()
        if token and token not in normalized:
            normalized.append(token)
    return normalized[:3]


def _stat_boxes(answer: Dict[str, Any], cards: Dict[str, str]) -> List[StatBox]:
    labels = [
        ("Goals", "goals"),
        ("Assists", "assists"),
        ("Points", "points"),
        ("P/GP", "ppg"),
        ("+/-", "+/-"),
    ]
    stat_source = answer.get("stats") if isinstance(answer.get("stats"), dict) else {}
    boxes: List[StatBox] = []
    for label, key in labels:
        value = _text(stat_source.get(key)) or _text(cards.get(label.lower())) or _text(cards.get(key))
        if value:
            boxes.append(StatBox(label=label, value=value, context="current_season"))
    return boxes


def build_player_profile_section(answer: Dict[str, Any]) -> UISection:
    cards = _card_map(answer)
    player = answer.get("player") if isinstance(answer.get("player"), dict) else {}
    identity = PlayerIdentity(
        full_name=_extract_player_name(answer),
        jersey_number=_extract_jersey_number(answer, cards),
        team=_text(player.get("team")) or _text(answer.get("team")) or _text(cards.get("team")),
        position=_text(player.get("position")) or _text(answer.get("position")) or _text(cards.get("position")),
        photo_url=_text(player.get("photo_url")) or _text(answer.get("photo_url")),
        status=_text(player.get("status")) or _text(answer.get("status")),
        assessment_badges=_assessment_badges(answer, cards),
    )
    return UISection(
        section_id="player_header",
        section_type="player_profile_header",
        title=identity.full_name,
        summary=_text(answer.get("public_comment") or answer.get("natural_language_response")),
        data={
            "identity": identity.__dict__,
            "stat_boxes": [box.__dict__ for box in _stat_boxes(answer, cards)],
            "required_fields": ["full_name", "jersey_number", "team", "position"],
        },
        default_open=True,
    )


def _evidence_items(answer: Dict[str, Any]) -> List[EvidenceItem]:
    items: List[EvidenceItem] = []
    for idx, fact in enumerate(_as_list(answer.get("observed_facts"), 12), start=1):
        text = _text(fact)
        if text:
            items.append(EvidenceItem(label=f"Evidence {idx}", value=text))
    for idx, item in enumerate(_as_list(answer.get("evidence"), 12), start=1):
        if isinstance(item, dict):
            value = _text(item.get("value") or item.get("summary") or item.get("text"))
            label = _text(item.get("label") or item.get("title")) or f"Evidence {idx}"
            source = _text(item.get("source")) or "athena"
            if value:
                items.append(EvidenceItem(label=label, value=value, source=source, confidence=item.get("confidence")))
        else:
            text = _text(item)
            if text:
                items.append(EvidenceItem(label=f"Evidence {idx}", value=text))
    return items


def _evidence_panel(answer: Dict[str, Any], evidence: List[EvidenceItem]) -> UISection:
    coverage = _coverage_categories(answer)
    limitations = _public_limitations(_as_list(answer.get("known_limitations"), 12))
    return UISection(
        section_id="evidence_panel",
        section_type="expandable_evidence_panel",
        title="Evidence & Coverage",
        summary="Evidence used and current coverage for this answer.",
        data={
            "evidence_used": coverage.get("current", []),
            "current_coverage": coverage,
            "observed_facts": [item.__dict__ for item in evidence],
            "limitations": limitations,
            "confidence": {
                "label": _confidence_label(answer.get("confidence")),
                "score": answer.get("confidence"),
            },
            "sources": [_text(item.get("source")) for item in _as_list(answer.get("sources"), 12) if isinstance(item, dict) and _text(item.get("source"))],
        },
        default_open=False,
    )


def build_athena_response(answer: Dict[str, Any], *, response_mode: str = "public") -> AthenaResponse:
    if not isinstance(answer, dict):
        answer = {"title": "Scout response", "public_comment": _text(answer), "natural_language_response": _text(answer)}
    intent = _text(answer.get("intent"))
    title = _text(answer.get("title")) or "Scout response"
    executive_summary = _text(answer.get("public_comment") or answer.get("natural_language_response") or answer.get("response_text")) or title
    evidence = _evidence_items(answer)
    confidence = ConfidenceSummary(
        label=_confidence_label(answer.get("confidence")),
        score=answer.get("confidence") if isinstance(answer.get("confidence"), (int, float)) else None,
    )
    key_findings = [_text(item) for item in _as_list(answer.get("key_findings"), 8) if _text(item)]
    if not key_findings:
        key_findings = [_text(item) for item in _as_list(answer.get("observed_facts"), 5) if _text(item)]
    ui_sections: List[UISection] = []
    is_player_response = intent in PLAYER_PROFILE_INTENTS or answer.get("player") or answer.get("player_name")
    if is_player_response:
        ui_sections.append(build_player_profile_section(answer))
        ui_sections.append(build_player_experience_section(answer))
    ui_sections.append(_evidence_panel(answer, evidence))
    return AthenaResponse(
        metadata=ExperienceMetadata(response_mode=response_mode, source_intent=intent),
        intent=intent,
        title=title,
        executive_summary=executive_summary,
        key_findings=key_findings,
        evidence=evidence,
        confidence=confidence,
        limitations=_public_limitations(_as_list(answer.get("known_limitations"), 12)),
        recommendations=[_text(item) for item in _as_list(answer.get("recommendations"), 8) if _text(item)],
        ui_sections=ui_sections,
    )


def attach_experience_contract(answer: Dict[str, Any], *, response_mode: str = "public") -> Dict[str, Any]:
    """Return a copy of an answer with an AthenaResponse render contract."""
    composed = dict(answer) if isinstance(answer, dict) else {"public_comment": _text(answer)}
    composed["athena_response"] = build_athena_response(composed, response_mode=response_mode).to_dict()
    composed["experience_contract"] = "athena_response_v1"
    return composed
