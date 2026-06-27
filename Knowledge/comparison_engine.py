"""
Athena Sports Intelligence Platform

Epic 4D.3b

Historical Comparison Orchestration
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, DefaultDict

from Core.json_utils import write_json
from Core.project_paths import OUTPUT_DIR

import Core.version as core_version
import Knowledge.Historical.version as historical_version

from .comparison import HistoricalComparator
from .comparison_models import HistoricalComparison
from .engine import build_historical_intelligence


HISTORICAL_COMPARISONS_FILE = "historical_comparisons.json"
HISTORICAL_COMPARISON_SUMMARY_FILE = "historical_comparison_summary.json"


def build_historical_comparisons(
    project_root: Path | None = None,
) -> dict[str, Any]:

    output_dir = (
        OUTPUT_DIR
        if project_root is None
        else Path(project_root) / "Output"
    )

    historical = build_historical_intelligence(
        project_root
    )

    series_payload = historical["series"]

    series_items = series_payload.get(
        "series",
        [],
    )

    comparisons: list[HistoricalComparison] = []

    skipped: list[dict[str, Any]] = []

    for series in series_items:

        snapshots = series.get(
            "snapshots",
            [],
        )

        if len(snapshots) < 2:
            skipped.append(
                {
                    "entity_id": series.get("entity_id"),
                    "reason": "fewer_than_two_snapshots",
                }
            )
            continue

        live_snapshots = []

        for snapshot in snapshots:

            from .models import HistoricalSnapshot, SnapshotType

            live_snapshots.append(
                HistoricalSnapshot(
                    id=snapshot["id"],
                    entity_id=snapshot["entity_id"],
                    snapshot_type=SnapshotType(
                        snapshot["snapshot_type"]
                    ),
                    captured_at=snapshot["captured_at"],
                    source=snapshot["source"],
                    confidence=snapshot["confidence"],
                    properties=snapshot.get(
                        "properties",
                        {},
                    ),
                )
            )

        live_snapshots = sorted(
            live_snapshots,
            key=lambda item: (
                item.captured_at,
                item.id,
            ),
        )

        for index in range(
            1,
            len(live_snapshots),
        ):

            comparisons.append(
                HistoricalComparator.compare(
                    live_snapshots[index - 1],
                    live_snapshots[index],
                )
            )

    by_change: DefaultDict[str, int] = defaultdict(int)

    by_entity: DefaultDict[str, int] = defaultdict(int)

    for comparison in comparisons:

        by_change[
            comparison.change.value
        ] += 1

        by_entity[
            comparison.entity_id
        ] += 1

    comparisons_payload = {
        "athena_version": core_version.ATHENA_VERSION,
        "historical_domain_version":
            historical_version.HISTORICAL_DOMAIN_VERSION,
        "historical_schema_version":
            historical_version.HISTORICAL_SCHEMA_VERSION,
        "historical_engine_version":
            historical_version.HISTORICAL_ENGINE_VERSION,
        "comparison_count": len(comparisons),
        "comparisons": [
            comparison.to_dict()
            for comparison in comparisons
        ],
    }

    summary = {
        "athena_version": core_version.ATHENA_VERSION,
        "historical_domain_version":
            historical_version.HISTORICAL_DOMAIN_VERSION,
        "historical_schema_version":
            historical_version.HISTORICAL_SCHEMA_VERSION,
        "historical_engine_version":
            historical_version.HISTORICAL_ENGINE_VERSION,
        "status": "ready"
        if comparisons
        else "insufficient_data",
        "comparison_count": len(comparisons),
        "skipped_count": len(skipped),
        "entities_with_comparisons": len(by_entity),
        "changes": dict(by_change),
        "comparisons_file": str(
            output_dir / HISTORICAL_COMPARISONS_FILE
        ),
    }

    write_json(
        output_dir / HISTORICAL_COMPARISONS_FILE,
        comparisons_payload,
    )

    write_json(
        output_dir / HISTORICAL_COMPARISON_SUMMARY_FILE,
        summary,
    )

    return {
        "summary": summary,
        "comparisons": comparisons_payload,
        "skipped": skipped,
    }


def comparisons_for_entity(
    entity_id: str,
    *,
    project_root: Path | None = None,
    limit: int = 20,
) -> dict[str, Any]:

    result = build_historical_comparisons(
        project_root
    )

    comparisons = [
        comparison
        for comparison in result["comparisons"].get(
            "comparisons",
            [],
        )
        if comparison.get("entity_id") == entity_id
    ]

    comparisons = comparisons[
        : max(1, int(limit or 20))
    ]

    return {
        "status": "available"
        if comparisons
        else "empty",
        "athena_version": core_version.ATHENA_VERSION,
        "historical_engine_version":
            historical_version.HISTORICAL_ENGINE_VERSION,
        "entity_id": entity_id,
        "comparison_count": len(comparisons),
        "comparisons": comparisons,
        "known_gaps": []
        if comparisons
        else [
            "No historical comparisons are currently available for the requested entity."
        ],
    }