"""
Athena Sports Intelligence Platform

Epic 4D.3a Validation

Historical Snapshot Foundation
"""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import Core.version as core_version
import Knowledge.Historical.version as historical_version

from Knowledge.Historical.builder import (
    build_historical_series,
    build_historical_snapshots,
)

from Knowledge.Historical.engine import (
    build_historical_intelligence,
    historical_series_for_entity,
)

from Knowledge.Historical.registry import (
    get_historical_registry,
)


passed = 0
failed = 0


def check(name, condition, detail=""):

    global passed, failed

    if condition:
        passed += 1
        print(f"[PASS] {name}: {detail}")
    else:
        failed += 1
        print(f"[FAIL] {name}: {detail}")


print("Historical Snapshot Foundation Validation Report")
print("=" * 55)

snapshots = build_historical_snapshots(PROJECT_ROOT)

series = build_historical_series(snapshots)

result = build_historical_intelligence(PROJECT_ROOT)

summary = result["summary"]

registry = get_historical_registry()

sample_entity = (
    series[0].entity_id
    if series
    else ""
)

entity_payload = (
    historical_series_for_entity(
        sample_entity,
        project_root=PROJECT_ROOT,
    )
    if sample_entity
    else {"status": "empty"}
)

check(
    "athena_version_present",
    bool(core_version.ATHENA_VERSION),
    core_version.ATHENA_VERSION,
)

check(
    "historical_domain_version_present",
    bool(historical_version.HISTORICAL_DOMAIN_VERSION),
    historical_version.HISTORICAL_DOMAIN_VERSION,
)

check(
    "historical_schema_version_present",
    bool(historical_version.HISTORICAL_SCHEMA_VERSION),
    historical_version.HISTORICAL_SCHEMA_VERSION,
)

check(
    "historical_engine_version_present",
    bool(historical_version.HISTORICAL_ENGINE_VERSION),
    historical_version.HISTORICAL_ENGINE_VERSION,
)

check(
    "snapshots_generated",
    len(snapshots) > 0,
    len(snapshots),
)

check(
    "series_generated",
    len(series) > 0,
    len(series),
)

check(
    "summary_ready",
    summary["status"] == "ready",
    summary,
)

check(
    "summary_version_matches_core",
    summary["athena_version"] == core_version.ATHENA_VERSION,
    summary["athena_version"],
)

check(
    "summary_historical_engine_version_matches_constant",
    summary["historical_engine_version"]
    == historical_version.HISTORICAL_ENGINE_VERSION,
    summary["historical_engine_version"],
)

check(
    "snapshot_count_matches",
    summary["snapshot_count"] == len(snapshots),
    summary["snapshot_count"],
)

check(
    "series_count_matches",
    summary["series_count"] == len(series),
    summary["series_count"],
)

check(
    "registry_snapshot_count_matches",
    registry.snapshot_count() == len(snapshots),
    registry.snapshot_count(),
)

check(
    "registry_entity_count_matches",
    registry.entity_count() == summary["entity_count"],
    registry.entity_count(),
)

sample_snapshot = snapshots[0]

serialized_snapshot = sample_snapshot.to_dict()

check(
    "snapshot_serializes",
    serialized_snapshot["id"] == sample_snapshot.id,
    serialized_snapshot,
)

check(
    "snapshot_has_entity",
    bool(sample_snapshot.entity_id),
    sample_snapshot.entity_id,
)

check(
    "snapshot_has_type",
    bool(sample_snapshot.snapshot_type.value),
    sample_snapshot.snapshot_type.value,
)

check(
    "snapshot_has_confidence",
    0.0 <= sample_snapshot.confidence <= 1.0,
    sample_snapshot.confidence,
)

sample_series = series[0]

serialized_series = sample_series.to_dict()

check(
    "series_serializes",
    serialized_series["entity_id"] == sample_series.entity_id,
    serialized_series,
)

check(
    "series_has_snapshots",
    serialized_series["snapshot_count"] > 0,
    serialized_series["snapshot_count"],
)

check(
    "series_confidence_normalized",
    0.0 <= sample_series.confidence <= 1.0,
    sample_series.confidence,
)

check(
    "entity_lookup_available",
    entity_payload["status"] == "available",
    entity_payload,
)

print()
print("=" * 55)

overall = "PASS" if failed == 0 else "FAIL"

print(f"Overall status: {overall}")
print(f"Passed: {passed}")
print("Warnings: 0")
print(f"Failed: {failed}")

raise SystemExit(0 if failed == 0 else 1)