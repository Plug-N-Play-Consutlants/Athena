"""Domain routing utilities for cross-domain propagation."""
from __future__ import annotations

from typing import Iterable, List

VALID_DOMAINS = {"player", "team", "prospect", "fantasy", "historical", "organization"}


def normalize_domains(domains: Iterable[str]) -> List[str]:
    normalized = []
    for domain in domains:
        value = str(domain or "").strip().lower()
        if value in VALID_DOMAINS and value not in normalized:
            normalized.append(value)
    return normalized
