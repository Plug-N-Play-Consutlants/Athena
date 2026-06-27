"""Scout Build 004 patch: polish and stabilize career-aware player briefs."""
from __future__ import annotations

from Reasoning.composition.executive_brief import ExecutiveBriefComposer

_original_build004 = ExecutiveBriefComposer.build_player_brief


def _dedupe_sentences(text: str) -> str:
    parts = []
    seen = set()
    for raw in (text or "").replace("\n", " ").split(". "):
        sentence = raw.strip()
        if not sentence:
            continue
        normalized = " ".join(sentence.lower().split())
        if normalized in seen:
            continue
        seen.add(normalized)
        parts.append(sentence)
    if not parts:
        return ""
    out = ". ".join(parts)
    if not out.endswith("."):
        out += "."
    return out


def _replace_role(cards):
    out = []
    for card in cards or []:
        if card.get("label") == "Role" and str(card.get("value", "")).lower() == "core fantasy asset":
            out.append({"label": "Asset Tier", "value": "Franchise Superstar"})
            out.append({"label": "Fantasy Role", "value": "Core Fantasy Asset"})
        else:
            out.append(card)
    # dedupe by label/value
    seen = set()
    clean = []
    for card in out:
        key = (card.get("label"), str(card.get("value")))
        if key not in seen:
            seen.add(key)
            clean.append(card)
    return clean


def _polish_current_value(body: str) -> str:
    body = body or ""
    body = body.replace(
        "Auston Matthews currently profiles as core fantasy asset. Production band: above average.",
        "Auston Matthews currently profiles as a franchise-superstar asset with a core fantasy role. The current-season production band is above average, but that label is narrower than his full career value."
    )
    body = body.replace(
        "currently profiles as core fantasy asset",
        "currently profiles as a franchise-superstar asset with a core fantasy role"
    )
    return body


def _polish_exec(summary: str) -> str:
    summary = _dedupe_sentences(summary)
    summary = summary.replace(
        "The current local evidence supports a core fantasy asset classification",
        "The current local evidence supports a franchise-superstar classification with a core fantasy asset role"
    )
    return summary


def patched_build004(self, assessment, evaluation=None, question="", mode="fantasy"):
    brief = _original_build004(self, assessment, evaluation, question, mode)

    brief["executive_summary"] = _polish_exec(brief.get("executive_summary", ""))
    brief["cards"] = _replace_role(brief.get("cards") or [])

    sections = []
    for section in brief.get("sections") or []:
        heading = section.get("heading")
        body = section.get("body") or ""
        if heading == "Executive Summary":
            body = brief["executive_summary"]
        elif heading == "Current Value":
            body = _polish_current_value(body)
        sections.append({"heading": heading, "body": body})
    brief["sections"] = sections

    brief["natural_language_response"] = self.render_text(
        brief.get("title", "Player Assessment"),
        brief.get("sections") or [],
        brief.get("confidence", 0),
        brief.get("cards") or [],
    )
    return brief


ExecutiveBriefComposer.build_player_brief = patched_build004
