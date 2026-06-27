"""Metadata helpers for canonical Trend Intelligence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from Core.version import ATHENA_VERSION
from Knowledge.Trends.version import TREND_DOMAIN_VERSION, TREND_SCHEMA_VERSION


def trend_metadata() -> Dict[str, Any]:
    """Return deterministic metadata for trend-domain artifacts."""

    return {
        "athena_version": ATHENA_VERSION,
        "trend_domain_version": TREND_DOMAIN_VERSION,
        "trend_schema_version": TREND_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "principle": "trends_are_derived_from_temporal_evidence",
    }
