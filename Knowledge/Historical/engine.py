"""
Athena Sports Intelligence Platform

Epic 4D.3a

Historical Snapshot Engine

Builds historical snapshots and series from temporal evidence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from Core.json_utils import write_json
from Core.project_paths import OUTPUT_DIR

import Core.version as core_version

from .builder import (
    build_historical_series,
    build_historical_snapshots,
)

from .registry import (
    get_historical_registry,
)

import Knowledge.Historical.version as historical_version


HISTORICAL_SNAPSHOTS_FILE = "historical_snapshots.json"

HISTORICAL_SERIES_FILE = "historical_series.json"

HISTORICAL_SUMMARY_FILE = "historical_intelligence_summary.json"


def build_historical_intelligence(
    project_root: Path | None = None,
) -> dict[str, Any]:

    output_dir = (
        OUTPUT_DIR
        if project_root is None
        else Path(project_root) / "Output"
    )

    snapshots = build_historical_snapshots(
        project_root
    )

    series = build_historical_series(
        snapshots
    )

    registry = get_historical_registry()

    registry.clear()

    registry.register_snapshots(
        snapshots
    )

    snapshots_payload = {
        "athena_version": core_version.ATHENA_VERSION,
        "historical_domain_version":
            historical_version.HISTORICAL_DOMAIN_VERSION,
        "historical_schema_version":
            historical_version.HISTORICAL_SCHEMA_VERSION,
        "historical_engine_version":
            historical_version.HISTORICAL_ENGINE_VERSION,
        "snapshot_count": len(snapshots),
        "snapshots": [
            snapshot.to_dict()
            for snapshot in snapshots
        ],
    }

    series_payload = {
        "athena_version": core_version.ATHENA_VERSION,
        "historical_domain_version":
            historical_version.HISTORICAL_DOMAIN_VERSION,
        "historical_schema_version":
            historical_version.HISTORICAL_SCHEMA_VERSION,
        "historical_engine_version":
            historical_version.HISTORICAL_ENGINE_VERSION,
        "series_count": len(series),
        "series": [
            item.to_dict()
            for item in series
        ],
    }

    by_type: dict[str, int] = {}

    by_entity: dict[str, int] = {}

    for snapshot in snapshots:

        by_type[
            snapshot.snapshot_type.value
        ] = by_type.get(
            snapshot.snapshot_type.value,
            0,
        ) + 1

        by_entity[
            snapshot.entity_id
        ] = by_entity.get(
            snapshot.entity_id,
            0,
        ) + 1

    summary = {
        "athena_version": core_version.ATHENA_VERSION,
        "historical_domain_version":
            historical_version.HISTORICAL_DOMAIN_VERSION,
        "historical_schema_version":
            historical_version.HISTORICAL_SCHEMA_VERSION,
        "historical_engine_version":
            historical_version.HISTORICAL_ENGINE_VERSION,
        "status": "ready" if snapshots else "empty",
        "snapshot_count": len(snapshots),
        "series_count": len(series),
        "entity_count": len(by_entity),
        "snapshot_types": by_type,
        "snapshots_file": str(
            output_dir / HISTORICAL_SNAPSHOTS_FILE
        ),
        "series_file": str(
            output_dir / HISTORICAL_SERIES_FILE
        ),
    }

    write_json(
        output_dir / HISTORICAL_SNAPSHOTS_FILE,
        snapshots_payload,
    )

    write_json(
        output_dir / HISTORICAL_SERIES_FILE,
        series_payload,
    )

    write_json(
        output_dir / HISTORICAL_SUMMARY_FILE,
        summary,
    )

    return {
        "summary": summary,
        "snapshots": snapshots_payload,
        "series": series_payload,
        "registry": {
            "snapshot_count": registry.snapshot_count(),
            "entity_count": registry.entity_count(),
        },
    }


def historical_series_for_entity(
    entity_id: str,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:

    build_historical_intelligence(
        project_root
    )

    registry = get_historical_registry()

    series = registry.build_series(
        entity_id
    )

    return {
        "status": "available" if series else "empty",
        "athena_version": core_version.ATHENA_VERSION,
        "historical_engine_version":
            historical_version.HISTORICAL_ENGINE_VERSION,
        "entity_id": entity_id,
        "series": series.to_dict() if series else None,
        "known_gaps": []
        if series
        else [
            "No historical snapshots are available for the requested entity."
        ],
    }


if __name__ == "__main__":

    result = build_historical_intelligence()

    summary = result["summary"]

    print("Athena Historical Intelligence")
    print("==============================")
    print(f"Status: {summary['status']}")
    print(f"Snapshots: {summary['snapshot_count']}")
    print(f"Series: {summary['series_count']}")
    print(f"Entities: {summary['entity_count']}")