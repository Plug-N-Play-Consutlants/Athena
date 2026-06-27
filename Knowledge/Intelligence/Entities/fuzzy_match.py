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
    if a in b or b in a:
        # Partial-name matches are useful but should not beat exact aliases.
        return max(0.82, SequenceMatcher(None, a, b).ratio())
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
