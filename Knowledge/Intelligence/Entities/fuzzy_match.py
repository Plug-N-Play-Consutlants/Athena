"""Small standard-library fuzzy matcher for public entity resolution."""

from __future__ import annotations

from difflib import SequenceMatcher
import re
from typing import Iterable, Tuple


def normalize_name(value: str) -> str:
    text = (value or "").lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def similarity(left: str, right: str) -> float:
    a = normalize_name(left)
    b = normalize_name(right)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    # A nickname embedded *inside* an unrelated word is never identity
    # evidence ("ove" in "improve", "mac" in "machine", etc.).  Only
    # complete lexical phrases count as an in-sentence entity mention.
    # For very short aliases (<=3 chars), only an entire query may match;
    # mentions inside longer questions are too collision-prone.
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    if len(shorter) <= 3 and a != b:
        return 0.0
    if len(shorter) > 3 and re.search(r"(?<!\w)" + re.escape(shorter) + r"(?!\w)", longer):
        return max(0.82, SequenceMatcher(None, a, b).ratio())
    # Fuzzy spelling repair is appropriate for a *name-like phrase*, not an
    # essay about a roster, team or trade. Long contextual inquiries must
    # contain an explicit player name rather than be edit-distance guessed.
    if max(len(a.split()), len(b.split())) > min(len(a.split()), len(b.split())) + 2:
        return 0.0
    if max(len(a), len(b)) > 3 * max(1, min(len(a), len(b))):
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def best_string_match(query: str, candidates: Iterable[str]) -> Tuple[str, float]:
    best = ""
    score = 0.0
    for candidate in candidates:
        current = similarity(query, candidate)
        if current > score:
            best = candidate
            score = current
    return best, round(score, 4)
