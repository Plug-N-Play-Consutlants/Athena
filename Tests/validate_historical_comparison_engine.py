"""
Athena Sports Intelligence Platform

Epic 4D.3b Validation

Historical Comparison Engine
"""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import Core.version as core_version
import Knowledge.Historical.version as historical_version

from Knowledge.Historical.comparison import (
    HistoricalComparator,
)

from Knowledge.Historical.comparison_engine import (
    build_historical_comparisons,
    comparisons_for_entity,
)

from Knowledge.Historical.engine import (
    build_historical_intelligence,
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


print("Historical Comparison Engine Validation Report")
print("=" * 55)

historical = build_historical_intelligence(PROJECT_ROOT)

series_items = historical["series"].get(
    "series",
    [],
)

comparison_result = build_historical_comparisons(
    PROJECT_ROOT,
)

summary = comparison_result["summary"]

comparisons = comparison_result["comparisons"].get(
    "comparisons",
    [],
)

skipped = comparison_result["skipped"]

sample_comparison = comparisons[0] if comparisons else None

sample_entity = (
    sample_comparison["entity_id"]
    if sample_comparison
    else ""
)

entity_payload = (
    comparisons_for_entity(
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
    "historical_series_available",
    len(series_items) > 0,
    len(series_items),
)

check(
    "comparisons_payload_available",
    isinstance(comparisons, list),
    type(comparisons).__name__,
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
    "summary_status_valid",
    summary["status"] in {
        "ready",
        "insufficient_data",
    },
    summary["status"],
)

check(
    "comparison_count_matches",
    summary["comparison_count"] == len(comparisons),
    summary["comparison_count"],
)

check(
    "skipped_count_matches",
    summary["skipped_count"] == len(skipped),
    summary["skipped_count"],
)

check(
    "some_entities_skipped_or_compared",
    (len(skipped) + len(comparisons)) > 0,
    {
        "skipped": len(skipped),
        "comparisons": len(comparisons),
    },
)

if sample_comparison:

    check(
        "sample_comparison_has_entity",
        bool(sample_comparison["entity_id"]),
        sample_comparison["entity_id"],
    )

    check(
        "sample_comparison_has_change",
        sample_comparison["change"]
        in {
            "improved",
            "declined",
            "stable",
            "unknown",
        },
        sample_comparison["change"],
    )

    check(
        "sample_comparison_confidence_normalized",
        0.0 <= sample_comparison["confidence"] <= 1.0,
        sample_comparison["confidence"],
    )

    check(
        "sample_comparison_deltas_present",
        isinstance(sample_comparison["deltas"], list),
        sample_comparison["delta_count"],
    )

    check(
        "entity_lookup_available",
        entity_payload["status"] == "available",
        entity_payload,
    )

else:

    check(
        "comparisons_absent_because_skipped",
        len(skipped) > 0,
        skipped[:3],
    )

print()
print("=" * 55)

overall = "PASS" if failed == 0 else "FAIL"

print(f"Overall status: {overall}")
print(f"Passed: {passed}")
print("Warnings: 0")
print(f"Failed: {failed}")

raise SystemExit(0 if failed == 0 else 1)