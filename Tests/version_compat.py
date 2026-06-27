"""Shared version assertions for Athena validators.

Accepts legacy Epic 4 drop naming and the locked Major.Epic.Sprint.Patch.Hotfix schema.
"""
from __future__ import annotations

import re

SEMVER5_RE = re.compile(r"^\d+\.\d+\.\d+\.\d+\.\d+$")
LEGACY_DROP_RE = re.compile(r"^0\.5\.0-drop\d+[a-z]\d+[a-z]?$", re.IGNORECASE)

def is_locked_version(value: str) -> bool:
    return bool(SEMVER5_RE.fullmatch(str(value or "")))

def is_legacy_drop_version(value: str) -> bool:
    return bool(LEGACY_DROP_RE.fullmatch(str(value or "")))

def is_recognized_athena_version(value: str) -> bool:
    return is_locked_version(value) or is_legacy_drop_version(value)

def is_recognized_scout_version(value: str, athena_version: str | None = None) -> bool:
    text = str(value or "")
    if athena_version and text == f"v{athena_version}":
        return True
    return text.startswith("v") and is_recognized_athena_version(text[1:])

def is_recognized_build(value: str, athena_version: str | None = None) -> bool:
    text = str(value or "")
    if is_locked_version(text):
        return True
    if text.startswith("drop"):
        return True
    if athena_version and text == athena_version:
        return True
    return False
