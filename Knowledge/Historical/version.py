"""
Athena Sports Intelligence Platform

Historical Intelligence version metadata.
"""

HISTORICAL_DOMAIN_VERSION = "4D.3a-historical-snapshot-foundation"

HISTORICAL_SCHEMA_VERSION = "historical-schema-v1"

HISTORICAL_ENGINE_VERSION = "4D.3a-historical-snapshot-foundation"

HISTORICAL_SYNTHESIS_VERSION = "4D.3d-historical-trend-synthesis"


def metadata() -> dict:

    return {
        "historical_domain_version": HISTORICAL_DOMAIN_VERSION,
        "historical_schema_version": HISTORICAL_SCHEMA_VERSION,
        "historical_engine_version": HISTORICAL_ENGINE_VERSION,
        "historical_synthesis_version": HISTORICAL_SYNTHESIS_VERSION,
    }
