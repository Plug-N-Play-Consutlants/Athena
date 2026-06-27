"""
Athena Sports Intelligence Platform

Epic 4D.3b Doctor

Historical Comparison Engine
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import Core.version as core_version
import Knowledge.Historical.version as historical_version

from Knowledge.Historical.comparison_engine import (
    build_historical_comparisons,
    comparisons_for_entity,
)


def _check(
    checks: list[dict[str, Any]],
    name: str,
    condition: bool,
    detail: Any = "",
) -> None:

    checks.append(
        {
            "name": name,
            "status": "PASS" if condition else "FAIL",
            "detail": detail,
        }
    )


def run_doctor(
    project_root: Path | None = None,
) -> dict[str, Any]:

    checks: list[dict[str, Any]] = []

    result = build_historical_comparisons(
        project_root
    )

    summary = result["summary"]

    comparisons = result["comparisons"].get(
        "comparisons",
        [],
    )

    skipped = result["skipped"]

    sample_entity = (
        comparisons[0].get("entity_id")
        if comparisons
        else ""
    )

    entity_payload = (
        comparisons_for_entity(
            sample_entity,
            project_root=project_root,
        )
        if sample_entity
        else {"status": "empty"}
    )

    _check(
        checks,
        "athena_version_present",
        bool(core_version.ATHENA_VERSION),
        core_version.ATHENA_VERSION,
    )

    _check(
        checks,
        "summary_version_matches_core",
        summary.get("athena_version")
        == core_version.ATHENA_VERSION,
        summary.get("athena_version"),
    )

    _check(
        checks,
        "historical_domain_version_present",
        bool(historical_version.HISTORICAL_DOMAIN_VERSION),
        historical_version.HISTORICAL_DOMAIN_VERSION,
    )

    _check(
        checks,
        "historical_schema_version_present",
        bool(historical_version.HISTORICAL_SCHEMA_VERSION),
        historical_version.HISTORICAL_SCHEMA_VERSION,
    )

    _check(
        checks,
        "historical_engine_version_present",
        bool(historical_version.HISTORICAL_ENGINE_VERSION),
        historical_version.HISTORICAL_ENGINE_VERSION,
    )

    _check(
        checks,
        "summary_historical_engine_version_matches_constant",
        summary.get("historical_engine_version")
        == historical_version.HISTORICAL_ENGINE_VERSION,
        summary.get("historical_engine_version"),
    )

    _check(
        checks,
        "summary_status_valid",
        summary.get("status")
        in {
            "ready",
            "insufficient_data",
        },
        summary.get("status"),
    )

    _check(
        checks,
        "comparisons_list_present",
        isinstance(comparisons, list),
        type(comparisons).__name__,
    )

    _check(
        checks,
        "comparison_count_matches",
        summary.get("comparison_count")
        == len(comparisons),
        summary.get("comparison_count"),
    )

    _check(
        checks,
        "skipped_count_matches",
        summary.get("skipped_count")
        == len(skipped),
        summary.get("skipped_count"),
    )

    _check(
        checks,
        "some_entities_processed",
        (len(comparisons) + len(skipped)) > 0,
        {
            "comparisons": len(comparisons),
            "skipped": len(skipped),
        },
    )

    if comparisons:

        sample = comparisons[0]

        _check(
            checks,
            "sample_comparison_has_entity",
            bool(sample.get("entity_id")),
            sample.get("entity_id"),
        )

        _check(
            checks,
            "sample_comparison_has_change",
            sample.get("change")
            in {
                "improved",
                "declined",
                "stable",
                "unknown",
            },
            sample.get("change"),
        )

        _check(
            checks,
            "sample_comparison_confidence_normalized",
            0.0 <= float(sample.get("confidence", 0.0)) <= 1.0,
            sample.get("confidence"),
        )

        _check(
            checks,
            "sample_comparison_has_deltas",
            isinstance(sample.get("deltas"), list),
            sample.get("delta_count"),
        )

        _check(
            checks,
            "entity_lookup_available",
            entity_payload.get("status") == "available",
            entity_payload,
        )

    else:

        _check(
            checks,
            "comparison_absence_explained_by_skips",
            len(skipped) > 0,
            skipped[:3],
        )

    failed = [
        check
        for check in checks
        if check["status"] != "PASS"
    ]

    return {
        "doctor": "historical_comparison_engine",
        "overall_status": "PASS" if not failed else "FAIL",
        "passed": len(checks) - len(failed),
        "failed": len(failed),
        "checks": checks,
    }


def main() -> int:

    report = run_doctor(PROJECT_ROOT)

    print("Historical Comparison Engine Doctor")
    print("=" * 45)
    print(f"Overall status: {report['overall_status']}")
    print(f"Passed: {report['passed']}")
    print(f"Failed: {report['failed']}")
    print()

    for check in report["checks"]:
        print(
            f"[{check['status']}] "
            f"{check['name']}: "
            f"{check['detail']}"
        )

    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())