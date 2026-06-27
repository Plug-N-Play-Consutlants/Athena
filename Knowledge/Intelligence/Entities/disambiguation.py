"""Disambiguation helpers for public entities."""

from __future__ import annotations

from typing import List

from .entity_extractor import EntityMatch


def disambiguation_lines(match: EntityMatch) -> List[str]:
    lines: List[str] = []
    for candidate in match.candidates:
        details = []
        if candidate.position:
            details.append(candidate.position)
        if candidate.team:
            details.append(candidate.team)
        if candidate.nationality:
            details.append(candidate.nationality)
        if candidate.birth_date:
            details.append(f"born {candidate.birth_date}")
        suffix = " — " + " / ".join(details) if details else ""
        summary = f"; {candidate.summary}" if candidate.summary else ""
        lines.append(f"{candidate.canonical_name}{suffix}{summary}")
    return lines
