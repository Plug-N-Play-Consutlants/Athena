"""
Athena Sports Intelligence Platform

Epic 4D.3a Doctor

Historical Snapshot Foundation
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

from Knowledge.Historical.engine import (
    build_historical_intelligence,
    historical_series_for_entity,
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

    result = build_historical_intelligence(
        project_root
    )

    summary = result["summary"]

    series_payload = result["series"]

    series_items = series_payload.get(
        "series",
        [],
    )

    sample_entity = (
        series_items[0].get("entity_id")
        if series_items
        else ""
    )

    entity_payload = (
        historical_series_for_entity(
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
        "engine_status_ready",
        summary.get("status") == "ready",
        summary,
    )

    _check(
        checks,
        "snapshots_generated",
        summary.get("snapshot_count", 0) > 0,
        summary.get("snapshot_count"),
    )

    _check(
        checks,
        "series_generated",
        summary.get("series_count", 0) > 0,
        summary.get("series_count"),
    )

    _check(
        checks,
        "entities_generated",
        summary.get("entity_count", 0) > 0,
        summary.get("entity_count"),
    )

    _check(
        checks,
        "registry_counts_present",
        result["registry"].get("snapshot_count", 0) > 0
        and result["registry"].get("entity_count", 0) > 0,
        result["registry"],
    )

    _check(
        checks,
        "sample_entity_lookup_available",
        entity_payload.get("status") == "available",
        entity_payload,
    )

    failed = [
        check
        for check in checks
        if check["status"] != "PASS"
    ]

    return {
        "doctor": "historical_snapshot_foundation",
        "overall_status": "PASS" if not failed else "FAIL",
        "passed": len(checks) - len(failed),
        "failed": len(failed),
        "checks": checks,
    }


def main() -> int:

    report = run_doctor(PROJECT_ROOT)

    print("Historical Snapshot Foundation Doctor")
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