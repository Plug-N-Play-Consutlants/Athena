"""Shared text normalization helpers for provider and knowledge boundaries."""
from __future__ import annotations

_MOJIBAKE_MARKERS = ("Ã", "Â", "â", "ð", "�")


def normalize_external_text(value: object, fallback: str = "") -> str:
    """Return external text with conservative UTF-8/Latin-1 mojibake repair.

    Provider payloads occasionally contain UTF-8 bytes that were decoded once as
    Latin-1/Windows-1252. Repair only strings carrying common mojibake markers;
    otherwise preserve the provider text exactly.
    """
    if value is None:
        return fallback
    text = str(value)
    if not any(marker in text for marker in _MOJIBAKE_MARKERS):
        return text
    for source_encoding in ("cp1252", "latin-1"):
        try:
            repaired = text.encode(source_encoding).decode("utf-8")
            if repaired:
                return repaired
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    return text
