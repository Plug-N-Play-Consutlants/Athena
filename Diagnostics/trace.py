"""Trace identifiers for Athena diagnostics."""

from __future__ import annotations

from datetime import datetime, timezone
from itertools import count

_COUNTER = count(1)


def new_trace_id(prefix: str = "trace") -> str:
    """Return a sortable human-readable trace id."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{prefix}-{stamp}-{next(_COUNTER):04d}"
