"""Recognize self-referential execution and capability diagnostics."""
from __future__ import annotations

import re


_DIAGNOSTIC_TARGET = re.compile(
    r"\b(?:rout(?:e|ing|ed)|fallback|pathway|pipeline|trace|evidence|"
    r"capabilit(?:y|ies)|module|execution|executed|source|provider|rules?)\b",
    re.I,
)
_SELF_REFERENCE = re.compile(
    r"\b(?:athena|scout|you|your|this answer|this response|this request)\b",
    re.I,
)
_ENGINE_NAME = re.compile(r"\b(?:athena|scout)\b", re.I)
_EXECUTION_TRACE_QUERY = re.compile(
    r"\b(?:what|which)\s+(?:intelligence\s+)?(?:modules?|capabilities|routes?)\s+"
    r"(?:were\s+)?(?:executed|used|selected|invoked|run)\b",
    re.I,
)


def is_diagnostic_inquiry(question: str) -> bool:
    """Match questions/statements about engine behavior, not hockey topics."""
    text = str(question or "").strip()
    if _EXECUTION_TRACE_QUERY.search(text):
        return True
    if not text or not _DIAGNOSTIC_TARGET.search(text):
        return False
    if _ENGINE_NAME.search(text):
        return True
    if not _SELF_REFERENCE.search(text):
        return False
    return bool(re.search(
        r"\b(?:rout(?:e|ing|ed)|fallback|pathway|pipeline|trace|evidence|"
        r"capabilit(?:y|ies)|module|execution|executed|source|provider)\b",
        text,
        re.I,
    ))
